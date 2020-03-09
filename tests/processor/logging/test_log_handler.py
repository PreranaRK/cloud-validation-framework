from processor.logging.log_handler import getlogger


def test_getlogger():
    logger = getlogger()
    assert logger is not None
    logger1 = getlogger()
    assert logger1 is not None
    assert id(logger) == id(logger1)

    
def test_parse_int():
    from processor.helper.config.config_utils import parseint
    val = parseint('23')
    assert val == 23
    val = parseint('ajey')
    assert val == 0
    val = parseint('ajey', 20)
    assert val == 20


def test_parse_bool():
    from processor.helper.config.config_utils import parsebool
    value = parsebool(5.6, True)
    assert value == True
    value = parsebool(True)
    assert value == True
    value = parsebool(0.6, True)
    assert value == False


def test_compare_in():
    from processor.comparison.comparisonantlr.compare_types import compare_in
    from processor.comparison.comparisonantlr.compare_types import EQ, NEQ, GT, GTE, LT, LTE
    val = compare_in('hi', 'hi', EQ)
    assert val == True
    val = compare_in('hello', 'man', EQ)
    assert val == False
    val = compare_in('hi', 0, EQ)
    assert val == False
