import json

import pytest

from yetiserver import model
from test.example_models import all_test_decision_trees, all_test_random_forests

def de_and_re_serialize(a_model):
    return json.loads(model.serialize(model.deserialize(json.dumps(a_model.get_original_json()))))

def test_serialize_inverse_deserialize_decision_tree():
    for tree in all_test_decision_trees:
        assert tree.get_original_json() == de_and_re_serialize(tree)

def test_serialize_inverse_deserialize_random_forest():
    for forest in all_test_random_forests:
        assert forest.get_original_json() == de_and_re_serialize(forest)
