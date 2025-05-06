import numpy as np

class MembershipFunction:
    def __init__(self, name, mf_type, params):
        self.name = name
        self.mf_type = mf_type
        self.params = params

    def compute(self, x):
        if self.mf_type == 'trapmf':
            return self.trapmf(x, self.params)
        elif self.mf_type == 'trimf':
            return self.trimf(x, self.params)
        else:
            raise ValueError(f"Unknown MF type: {self.mf_type}")

    @staticmethod
    def trapmf(x, params):
        a, b, c, d = params
        if x <= a or x >= d:
            return 0.0
        elif a < x < b:
            return (x - a) / (b - a) if b != a else 1.0
        elif b <= x <= c:
            return 1.0
        elif c < x < d:
            return (d - x) / (d - c) if d != c else 1.0
        else:
            return 0.0

    @staticmethod
    def trimf(x, params):
        a, b, c = params
        if x <= a or x >= c:
            return 0.0
        elif a < x < b:
            return (x - a) / (b - a) if b != a else 1.0
        elif b == x:
            return 1.0
        elif b < x < c:
            return (c - x) / (c - b) if c != b else 1.0
        else:
            return 0.0

class FuzzyVariable:
    def __init__(self, name, var_range, mfs):
        self.name = name
        self.range = var_range  # tuple (min, max)
        self.mfs = mfs  # list of MembershipFunction

    def fuzzify(self, x):
        # Returns dict of mf_name: membership_value
        fuzzified = {}
        for mf in self.mfs:
            fuzzified[mf.name] = mf.compute(x)
        return fuzzified

class FuzzyRule:
    def __init__(self, antecedent_indices, consequent_index, weight=1.0):
        # antecedent_indices: list of input MF indices (1-based)
        # consequent_index: output MF index (1-based)
        self.antecedent_indices = antecedent_indices
        self.consequent_index = consequent_index
        self.weight = weight

class MamdaniFIS:
    def __init__(self, name, inputs, output, rules,
                 and_method='min', or_method='max',
                 imp_method='min', agg_method='max',
                 defuzz_method='centroid'):
        self.name = name
        self.inputs = inputs  # list of FuzzyVariable
        self.output = output  # FuzzyVariable
        self.rules = rules  # list of FuzzyRule
        self.and_method = and_method
        self.or_method = or_method
        self.imp_method = imp_method
        self.agg_method = agg_method
        self.defuzz_method = defuzz_method

    def _and(self, a, b):
        if self.and_method == 'min':
            return min(a, b)
        elif self.and_method == 'prod':
            return a * b
        else:
            raise ValueError(f"Unknown AND method: {self.and_method}")

    def _or(self, a, b):
        if self.or_method == 'max':
            return max(a, b)
        elif self.or_method == 'sum':
            return a + b - a * b
        else:
            raise ValueError(f"Unknown OR method: {self.or_method}")

    def _implication(self, antecedent_value, consequent_mf_value):
        if self.imp_method == 'min':
            return min(antecedent_value, consequent_mf_value)
        elif self.imp_method == 'prod':
            return antecedent_value * consequent_mf_value
        else:
            raise ValueError(f"Unknown Implication method: {self.imp_method}")

    def _aggregation(self, a, b):
        if self.agg_method == 'max':
            return max(a, b)
        elif self.agg_method == 'sum':
            return a + b - a * b
        else:
            raise ValueError(f"Unknown Aggregation method: {self.agg_method}")

    def _defuzzify(self, x, aggregated_mf):
        if self.defuzz_method == 'centroid':
            numerator = np.sum(x * aggregated_mf)
            denominator = np.sum(aggregated_mf)
            if denominator == 0:
                # Avoid division by zero, return midpoint of output range
                return (self.output.range[0] + self.output.range[1]) / 2
            return numerator / denominator
        else:
            raise ValueError(f"Unknown Defuzzification method: {self.defuzz_method}")

    def evaluate(self, input_values):
        """
        input_values: list of input crisp values, length must match number of inputs
        Returns crisp output value
        """
        if len(input_values) != len(self.inputs):
            raise ValueError("Number of inputs does not match")

        # Step 1: Fuzzify inputs
        fuzzified_inputs = []
        for i, val in enumerate(input_values):
            fuzzified = self.inputs[i].fuzzify(val)
            fuzzified_inputs.append(fuzzified)

        # Step 2: Evaluate rules
        # For each rule, compute firing strength
        rule_strengths = []
        for rule in self.rules:
            # antecedent_indices are 1-based indices of MF for each input
            antecedent_values = []
            for input_idx, mf_idx in enumerate(rule.antecedent_indices):
                # mf_idx is 1-based index of MF in input variable
                mf_name = self.inputs[input_idx
