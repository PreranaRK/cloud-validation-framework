import os

def mock_getenv(key, default=None):
    return 'clientSecret'


def mock_empty_getenv(key, default=None):
    return default


def mock_input(text):
    return 'clientSecret'


def mock_valid_http_post_request(url, data, headers={}):
    return 200, {'access_token': 'abcd'}

def mock_invalid_http_post_request(url, data, headers={}):
    return 401, {'access_token': None}


def mock_get_from_currentdata(key):
    if key == 'subscriptionId':
        return 'subscriptionId'
    elif key == 'tenant_id':
        return 'tenant_id'
    elif key == 'clientId':
        return 'clientId'
    elif key == 'rg':
        return 'rg'
    else:
        return None

def mock_empty_get_from_currentdata(key):
    if key == 'subscriptionId':
        return 'subscriptionId'
    elif key == 'tenant_id':
        return 'tenant_id'
    else:
        return None

def test_get_azure_functions(monkeypatch):
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.get_from_currentdata',
                        mock_get_from_currentdata)
    monkeypatch.setattr(os, 'getenv', mock_getenv)
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.input', mock_input)
    from processor.helper.httpapi.restapi_azure import get_subscription_id,\
        get_tenant_id, get_client_id, get_resource_group, get_client_secret
    assert 'subscriptionId' == get_subscription_id()
    assert 'tenant_id' == get_tenant_id()
    assert 'clientId' == get_client_id()
    assert 'rg' == get_resource_group()
    assert 'clientSecret' == get_client_secret()


def test_web_client_data(monkeypatch):
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.get_from_currentdata',
                        mock_get_from_currentdata)
    monkeypatch.setattr(os, 'getenv', mock_empty_getenv)
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.input', mock_input)
    from processor.helper.httpapi.restapi_azure import get_client_secret, get_web_client_data
    assert 'clientSecret' == get_client_secret()
    client_id, client_secret, sub_name, sub_id, tenant_id = \
        get_web_client_data('azure', 'azureStructure.json', 'ajeybk1@kbajeygmail.onmicrosoft.com')
    assert client_id is not None
    assert client_secret is not None
    assert sub_id is not None
    assert sub_name is not None
    assert tenant_id is not None


def test_get_access_token(monkeypatch):
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.get_from_currentdata',
                        mock_get_from_currentdata)
    monkeypatch.setattr(os, 'getenv', mock_getenv)
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.http_post_request',
                        mock_valid_http_post_request)
    from processor.helper.httpapi.restapi_azure import get_access_token
    val = get_access_token()
    assert val == 'abcd'


def test_none_get_access_token(monkeypatch):
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.get_from_currentdata',
                        mock_empty_get_from_currentdata)
    monkeypatch.setattr(os, 'getenv', mock_getenv)
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.http_post_request',
                        mock_valid_http_post_request)
    from processor.helper.httpapi.restapi_azure import get_access_token
    val = get_access_token()
    assert val is None


def test_invalid_http_get_access_token(monkeypatch):
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.get_from_currentdata',
                        mock_get_from_currentdata)
    monkeypatch.setattr(os, 'getenv', mock_getenv)
    monkeypatch.setattr('processor.helper.httpapi.restapi_azure.http_post_request',
                        mock_invalid_http_post_request)
    from processor.helper.httpapi.restapi_azure import get_access_token
    val = get_access_token()
    assert val is None