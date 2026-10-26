import unittest
import pandas as pd
import numpy as np
from freshwise.forecast import predict
from freshwise.data import enrich

class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame({"week":[1,2], "center_id":[1,1], "meal_id":[10,10], "num_orders":[10,30]})
        self.future = pd.DataFrame({"week":[3,3], "center_id":[1,2], "meal_id":[10,10], "num_orders":[999,999]})
    def test_outcomes_never_used(self):
        first = predict(self.history,self.future)
        changed = self.future.assign(num_orders=0)
        np.testing.assert_equal(first,predict(self.history,changed))
        np.testing.assert_equal(first,[20,20])
    def test_unseen_meal_fallback(self):
        future = self.future.assign(meal_id=99)
        np.testing.assert_equal(predict(self.history,future),[20,20])
    def test_last(self):
        self.assertEqual(predict(self.history,self.future,"last")[0],30)
    def test_duplicate_dimension_rejected(self):
        meals = pd.DataFrame({"meal_id":[10,10],"category":["A","B"]})
        centers = pd.DataFrame({"center_id":[1],"center_type":["A"]})
        with self.assertRaises(pd.errors.MergeError):
            enrich(self.history,meals,centers)
