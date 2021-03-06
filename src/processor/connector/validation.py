"""
   Common file for running validations.
"""
import json
import re
import pymongo
import copy 

from collections import defaultdict
from processor.logging.log_handler import getlogger
from processor.comparison.interpreter import Comparator
from processor.helper.json.json_utils import get_field_value, get_json_files,\
    json_from_file, TEST, collectiontypes, SNAPSHOT, JSONTEST, MASTERTEST, get_field_value_with_default
from processor.helper.config.config_utils import config_value, get_test_json_dir,\
    DATABASE, DBNAME, SINGLETEST, framework_dir
from processor.database.database import create_indexes, COLLECTION,\
    sort_field, get_documents
from processor.reporting.json_output import dump_output_results
from processor.helper.config.rundata_utils import get_dbtests, get_from_currentdata


logger = getlogger()


def get_snapshot_id_to_collection_dict(snapshot_file, container, dbname, filesystem=True):
    snapshot_data = {}
    snapshot_json_data = {}
    if filesystem:
        file_name = '%s.json' % snapshot_file if snapshot_file and not \
            snapshot_file.endswith('.json') else snapshot_file
        snapshot_file = '%s/%s/%s' % (get_test_json_dir(), container, file_name)
        snapshot_json_data = json_from_file(snapshot_file)
    else:
        parts = snapshot_file.split('.')
        collection = config_value(DATABASE, collectiontypes[SNAPSHOT])
        qry = {'container': container, 'name': parts[0]}
        sort = [sort_field('timestamp', False)]
        docs = get_documents(collection, dbname=dbname, sort=sort, query=qry, limit=1)
        logger.info('Number of Snapshot Documents: %s', len(docs))
        if docs and len(docs):
            snapshot_json_data = docs[0]['json']
    snapshots = get_field_value(snapshot_json_data, 'snapshots')
    if not snapshots:
        logger.info("Snapshot does not contain snapshots...")
        return snapshot_data
    for snapshot in snapshots:
        nodes = get_field_value(snapshot, 'nodes')
        if not nodes:
            logger.info("No nodes in snapshot, continuing to next!...")
            continue
        for node in nodes:
            sid = get_field_value(node, 'snapshotId')
            coll = node['collection'] if 'collection' in node else COLLECTION
            collection = coll.replace('.', '').lower()
            snapshot_data[sid] = collection
            if get_dbtests():
                create_indexes(collection, dbname, [('timestamp', pymongo.TEXT)])
    return snapshot_data


def run_validation_test(version, container, dbname, collection_data, testcase):
    comparator = Comparator(version, container, dbname, collection_data, testcase)
    result_val = comparator.validate()
    result_val.update(testcase)
    return result_val


def run_file_validation_tests(test_file, container, filesystem=True, snapshot_status=None):
    logger.info("*" * 50)
    logger.info("validator tests: %s", test_file)
    test_json_data = json_from_file(test_file)
    if not test_json_data:
        logger.info("Test file %s looks to be empty, next!...", test_file)
    singletest = get_from_currentdata(SINGLETEST)
    if singletest:
        testsets = get_field_value_with_default(test_json_data, 'testSet', [])
        for testset in testsets:
            newtestcases = []
            for testcase in testset['cases']:
                if ('testId' in testcase and testcase['testId'] == singletest) or \
                        ('masterTestId' in testcase and testcase['masterTestId'] == singletest):
                    newtestcases.append(testcase)
            testset['cases'] = newtestcases
    resultset = run_json_validation_tests(test_json_data, container, filesystem, snapshot_status)
    finalresult = True
    if resultset:
        snapshot = test_json_data['snapshot'] if 'snapshot' in test_json_data else ''
        if singletest:
            print(json.dumps(resultset, indent=2))
        else:
            dump_output_results(resultset, container, test_file, snapshot, filesystem)
        for result in resultset:
            if 'result' in result:
                if not re.match(r'passed', result['result'], re.I):
                    finalresult = False
                    break
    else:
        # TODO: NO test cases in this file.
        # LOG HERE that no test cases are present in this file.
        finalresult = False
    return finalresult


def run_json_validation_tests(test_json_data, container, filesystem=True, snapshot_status=None):
    resultset = []
    if not test_json_data:
        return resultset
    if not snapshot_status:
        snapshot_status = {}
    logger.debug(json.dumps(test_json_data, indent=2))
    testsets = get_field_value(test_json_data, 'testSet')
    if not testsets or not isinstance(testsets, list):
        logger.info("Test json does not contain testset, next!...")
        return resultset
    dbname = config_value(DATABASE, DBNAME)
    # Populate the snapshotId => collection for the snapshot.json in the test file.
    collection_data = get_snapshot_id_to_collection_dict(test_json_data['snapshot'],
                                                         container, dbname, filesystem)
    if test_json_data['snapshot'] in snapshot_status:
        current_snapshot_status = snapshot_status[test_json_data['snapshot']]
    else:
        current_snapshot_status = {}
    for testset in testsets:
        version = get_field_value(testset, 'version')
        testcases = get_field_value(testset, 'cases')
        if not testcases or not isinstance(testcases, list):
            logger.info("No testcases in testSet!...")
            continue
        for testcase in testset['cases']:
            result_val = run_validation_test(version, container, dbname, collection_data,
                                             testcase)
            resultset.append(result_val)
    return resultset


def run_container_validation_tests(container, dbsystem=True, snapshot_status=None):
    if not snapshot_status:
        snapshot_status = {}
    if dbsystem:
        return run_container_validation_tests_database(container, snapshot_status)
    else:
        return run_container_validation_tests_filesystem(container, snapshot_status)


def run_container_validation_tests_filesystem(container, snapshot_status=None):
    """Get test files from the filesystem."""
    logger.info("Starting validation tests")
    reporting_path = config_value('REPORTING', 'reportOutputFolder')
    json_dir = '%s/%s/%s' % (framework_dir(), reporting_path, container)
    logger.info(json_dir)
    test_files = get_json_files(json_dir, JSONTEST)
    logger.info('\n'.join(test_files))
    result = True
    for test_file in test_files:
        val = run_file_validation_tests(test_file, container, True, snapshot_status)
        result = result and val
    # mastertest files
    test_files = get_json_files(json_dir, MASTERTEST)
    logger.info('\n'.join(test_files))
    finalresult = True
    for test_file in test_files:
        logger.info("*" * 50)
        logger.info("validator tests: %s", test_file)
        test_json_data = json_from_file(test_file)
        if not test_json_data:
            logger.info("Test file %s looks to be empty, next!...", test_file)
            continue
        snapshot_key = '%s_gen' % test_json_data['masterSnapshot']
        mastersnapshots = defaultdict(list)
        snapshot_data = snapshot_status[snapshot_key] if snapshot_key in snapshot_status else {}
        for snapshot_id, mastersnapshot_id in snapshot_data.items():
            if isinstance(mastersnapshot_id, list):
                for master_snapshot_id in mastersnapshot_id:
                    mastersnapshots[master_snapshot_id].append(snapshot_id)
            elif isinstance(mastersnapshot_id, str):
                mastersnapshots[mastersnapshot_id].append(snapshot_id)
        test_json_data['snapshot'] = snapshot_key
        testsets = get_field_value_with_default(test_json_data, 'testSet', [])
        for testset in testsets:
            testcases = get_field_value_with_default(testset, 'cases', [])
            testset['cases'] = _get_new_testcases(testcases, mastersnapshots)
        # print(json.dumps(test_json_data, indent=2))
        singletest = get_from_currentdata(SINGLETEST)
        if singletest:
            for testset in testsets:
                newtestcases = []
                for testcase in testset['cases']:
                    if ('testId' in testcase and  testcase['testId'] == singletest) or \
                            ('masterTestId' in testcase and testcase['masterTestId'] == singletest):
                        newtestcases.append(testcase)
                testset['cases'] = newtestcases
        resultset = run_json_validation_tests(test_json_data, container, False, snapshot_status)
        if resultset:
            snapshot = test_json_data['snapshot'] if 'snapshot' in test_json_data else ''
            if singletest:
                print(json.dumps(resultset, indent=2))
            else:
                dump_output_results(resultset, container, test_file, snapshot, True)
            for result in resultset:
                if 'result' in result:
                    if not re.match(r'passed', result['result'], re.I):
                        finalresult = False
                        break
        else:
            logger.info('No mastertest Documents found!')
            finalresult = False
    return finalresult


def _get_snapshot_type_map(container):
    dbname = config_value(DATABASE, DBNAME)
    collection = config_value(DATABASE, collectiontypes[SNAPSHOT])
    qry = {'container': container}
    docs = get_documents(collection, dbname=dbname, query=qry)
    mappings = {}
    if docs and len(docs):
        for doc in docs:
            given_data = doc['json']
            if given_data:
                snapshots = given_data.get("snapshots", [])
                for snapshot in snapshots:
                    given_type = snapshot.get("type","")
                    if given_type == "aws":
                        nodes = snapshot.get("nodes",[])
                        for node in nodes:
                            mappings[node['snapshotId']] = node['type']
    return mappings


def run_container_validation_tests_database(container, snapshot_status=None):
    """ Get the test files from the database"""
    dbname = config_value(DATABASE, DBNAME)
    # For test files
    collection = config_value(DATABASE, collectiontypes[TEST])
    qry = {'container': container}
    sort = [sort_field('timestamp', False)]
    docs = get_documents(collection, dbname=dbname, sort=sort, query=qry)
    finalresult = True
    if docs and len(docs):
        logger.info('Number of test Documents: %s', len(docs))
        for doc in docs:
            if doc['json']:
                resultset = run_json_validation_tests(doc['json'], container, False)
                if resultset:
                    snapshot = doc['json']['snapshot'] if 'snapshot' in doc['json'] else ''
                    test_file = doc['name'] if 'name' in doc else ''
                    dump_output_results(resultset, container, test_file, snapshot, False)
                    for result in resultset:
                        if 'result' in result:
                            if not re.match(r'passed', result['result'], re.I):
                                finalresult = False
                                break
    else:
        logger.info('No test Documents found!')
        finalresult = False
    # For mastertest files
    collection = config_value(DATABASE, collectiontypes[MASTERTEST])
    docs = get_documents(collection, dbname=dbname, sort=sort, query=qry)
    # snapshots_details_map = _get_snapshot_type_map(container)
    if docs and len(docs):
        logger.info('Number of mastertest Documents: %s', len(docs))
        for doc in docs:
            test_json_data = doc['json']
            if test_json_data:
                snapshot_key = '%s_gen' % test_json_data['masterSnapshot']
                mastersnapshots = defaultdict(list)
                snapshot_data = snapshot_status[snapshot_key] if snapshot_key in snapshot_status else {}
                for snapshot_id, mastersnapshot_id in snapshot_data.items():
                    if isinstance(mastersnapshot_id, list):
                        for msnp_id in mastersnapshot_id:
                            mastersnapshots[msnp_id].append(snapshot_id)    
                    else:
                        mastersnapshots[mastersnapshot_id].append(snapshot_id)
                test_json_data['snapshot'] = snapshot_key
                testsets = get_field_value_with_default(test_json_data, 'testSet', [])
                for testset in testsets:
                    testcases = get_field_value_with_default(testset, 'cases', [])
                    testset['cases'] = _get_new_testcases(testcases, mastersnapshots)
                # print(json.dumps(test_json_data, indent=2))
                resultset = run_json_validation_tests(test_json_data, container, False, snapshot_status)
                if resultset:
                    snapshot = doc['json']['snapshot'] if 'snapshot' in doc['json'] else ''
                    test_file = doc['name'] if 'name' in doc else ''
                    dump_output_results(resultset, container, test_file, snapshot, False)
                    for result in resultset:
                        if 'result' in result:
                            if not re.match(r'passed', result['result'], re.I):
                                finalresult = False
                                break
    else:
        logger.info('No mastertest Documents found!')
        finalresult = False
    return finalresult


def _get_new_testcases(testcases, mastersnapshots):
    newcases = []
    for testcase in testcases:
        test_parser_type = testcase.get('type', None)
        if test_parser_type == 'rego':
            new_cases = _get_rego_testcase(testcase, mastersnapshots)
            newcases.extend(new_cases)
        else:
            rule_str = get_field_value_with_default(testcase, 'rule', '')
            ms_ids = re.findall(r'\{(.*)\}', rule_str)
            # detail_method = get_field_value(testcase, 'detailMethod')
            for ms_id in ms_ids:
                for s_id in mastersnapshots[ms_id]:
                    # new_rule_str = re.sub('{%s}' % ms_id, '{%s}' % s_id, rule_str)
                    # if not detail_method or detail_method == snapshots_details_map[s_id]:
                    new_rule_str = rule_str.replace('{%s}' % ms_id, '{%s}' % s_id)
                    new_testcase = {'title': testcase.get('title') if testcase.get('title') else "", 'description': testcase.get('description') if testcase.get('description') else "", 'rule': new_rule_str, 'testId': testcase['masterTestId']}
                    newcases.append(new_testcase)
    return newcases

def _get_rego_testcase(testcase, mastersnapshots):
    is_first = True
    newcases = []
    ms_ids = testcase.get('masterSnapshotId')
    service = ms_ids[0].split('_')[1]
    for ms_id in ms_ids:
        for s_id in mastersnapshots[ms_id]:
            # new_rule_str = re.sub('{%s}' % ms_id, '{%s}' % s_id, rule_str)
            # if not detail_method or detail_method == snapshots_details_map[s_id]:
            new_testcase = copy.copy(testcase)
            if service not in ms_id:
                if s_id.split('_')[1] not in newcases[0]['snapshotId'][-1]:
                    [newcase['snapshotId'].append(s_id) for newcase in newcases]
                else:
                    new_cases = copy.deepcopy(newcases)
                    [new_case['snapshotId'].pop(-1) and new_case['snapshotId'].append(s_id) for new_case in new_cases]
                    newcases.extend(new_cases)
                continue    
            new_testcase['snapshotId'] = [s_id]
            newcases.append(new_testcase)
    return newcases


def container_snapshots_filesystem(container):
    """Get snapshot list used in test files from the filesystem."""
    snapshots = []
    logger.info("Starting to get list of snapshots")
    reporting_path = config_value('REPORTING', 'reportOutputFolder')
    json_dir = '%s/%s/%s' % (framework_dir(), reporting_path, container)
    logger.info(json_dir)
    test_files = get_json_files(json_dir, JSONTEST)
    logger.info('\n'.join(test_files))
    for test_file in test_files:
        test_json_data = json_from_file(test_file)
        if test_json_data:
            snapshot = test_json_data['snapshot'] if 'snapshot' in test_json_data else ''
            if snapshot:
                snapshots.append(snapshot)
    return snapshots

def main(container):
    run_container_validation_tests_filesystem(container)


if __name__ == '__main__':
    import sys
    from processor.logging.log_handler import getlogger, init_logger, NONE
    init_logger(NONE)
    if len(sys.argv) > 1:
        main(sys.argv[1])