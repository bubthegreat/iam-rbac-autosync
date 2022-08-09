import yaml
import pytest


@pytest.fixture(scope='function')
def dev_rbac_mapper():
    with open('tests/fixtures/dev-iam-rbac-autosync.yaml', "r") as stream:
        yaml_obj = yaml.safe_load(stream)
    return yaml_obj


@pytest.fixture(scope='function')
def prod_rbac_mapper():
    with open('tests/fixtures/prod-iam-rbac-autosync.yaml', "r") as stream:
        yaml_obj = yaml.safe_load(stream)
    return yaml_obj


@pytest.fixture(scope='function')
def dev_aws_auth_configmap():
    with open('tests/fixtures/dev-aws-auth-configmap.yaml', "r") as stream:
        yaml_obj = yaml.safe_load(stream)
    return yaml_obj


@pytest.fixture(scope='function')
def prod_aws_auth_configmap():
    with open('tests/fixtures/prod-aws-auth-configmap.yaml', "r") as stream:
        yaml_obj = yaml.safe_load(stream)
    return yaml_obj
