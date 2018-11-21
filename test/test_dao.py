import unittest.mock as mock

import pytest
import redis

from test.example_models import credit_score_decision_tree, credit_score_random_forest
from yetiserver import model
from test.fixtures import dao


def test_raise_exception_on_failure_to_connect_to_db(dao):
    class RedisExceptionThrower:
        def __init__(self, *args, **kwargs):
            raise redis.RedisError

    with pytest.raises(redis.RedisError):
        dao._get_redis_connection(redis_class=RedisExceptionThrower)


def test_setting_connection_parameters_changes_connection_details(dao):
    class RedisRememberArgs:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    before_host, before_port, before_pass = dao.__host, dao.__port, dao.__password
    dao.set_redis_connection_parameters("host", "port", "pass")

    r = dao._get_redis_connection(redis_class=RedisRememberArgs)
    assert r.kwargs['host'] == "host"
    assert r.kwargs['port'] == "port"
    assert r.kwargs['password'] == "pass"

    dao.set_redis_connection_parameters(before_host, before_port, before_pass)


def test_attempt_to_retrieve_model_doesnt_exist_returns_none(dao):
    assert dao.retrieve_model("nonexistent_user", "model1") is None
    assert dao.retrieve_model("user1", "no_such_model") is None


def test_attempt_to_store_invalid_model_returns_false(dao):
    assert not dao.store_model("user1", "model1", "ahaha not a model")


def test_storing_model_in_correct_place(dao):
    user = "user1"
    model_name = "model1"
    mock_conn = mock.Mock()

    dao.store_model(user, model_name, credit_score_decision_tree, rconn=mock_conn)

    expected_key = dao.__key_for_model(user, model_name)
    expected_value = model.serialize(credit_score_decision_tree)
    mock_conn.set.assert_called_once_with(expected_key, expected_value)


def test_retrieving_model_looks_in_correct_place(dao):
    user = "user1"
    model_name = "model1"
    mock_conn = mock.Mock()

    dao.retrieve_model(user, model_name, rconn=mock_conn)

    expected_key = dao.__key_for_model(user, model_name)
    mock_conn.get.assert_called_once_with(expected_key)

@pytest.mark.integration
@pytest.mark.requires_local_redis
def test_can_connect_to_local_redis(dao):
    conn = dao._get_redis_connection()
    assert conn

@pytest.mark.integration
@pytest.mark.requires_local_redis
def test_can_store_retrieve_decision_tree(dao):
    success = dao.store_model("user1", "model1", credit_score_decision_tree)
    assert success
    model = dao.retrieve_model("user1", "model1")
    assert credit_score_decision_tree.get_original_json() == model.get_original_json()

@pytest.mark.integration
@pytest.mark.requires_local_redis
def test_can_store_retrieve_random_forest(dao):
    success = dao.store_model("user1", "model1", credit_score_random_forest)
    assert success
    model = dao.retrieve_model("user1", "model1")
    assert credit_score_random_forest.get_original_json() == model.get_original_json()

@pytest.mark.integration
@pytest.mark.requires_local_redis
def test_retrieved_model_same_as_original_model(dao):
    dao.store_model("user2", "model2", credit_score_decision_tree)
    retrieved_model = dao.retrieve_model("user2", "model2")
    for (income, credit) in [(100, 100), (100_000, 100), (100_000, 1000), (100, 1000)]:
        data = {"income": income, "credit score": credit}
        assert credit_score_decision_tree(data) == retrieved_model(data)
