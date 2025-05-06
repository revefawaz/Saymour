import numpy as np

def trapmf(x, params):
    a, b, c, d = params
    y = np.zeros_like(x, dtype=float)
    # ascending slope
    idx = np.logical_and(a < x, x < b)
    y[idx] = (x[idx] - a) / (b - a)
    # top
    idx = np.logical_and(b <= x, x <= c)
    y[idx] = 1.0
    # descending slope
    idx = np.logical_and(c < x, x < d)
    y[idx] = (d - x[idx]) / (d - c)
    return y

def trimf(x, params):
    a, b, c = params
    y = np.zeros_like(x, dtype=float)
    # ascending slope
    idx = np.logical_and(a < x, x < b)
    y[idx] = (x[idx] - a) / (b - a)
    # top
    y[x == b] = 1.0
    # descending slope
    idx = np.logical_and(b < x, x < c)
    y[idx] = (c - x[idx]) / (c - b)
    return y

class FuzzyForDistance:
    def __init__(self):
        # Input1: 'distance from the person' [0 80]
        self.in1_name = 'distance from the person'
        self.in1_range = (0, 80)
        # MFs for Input1
        self.in1_MFs = {
            'near': ('trapmf', [0, 0, 15, 30]),
            'medium': ('trimf', [20, 40, 60]),
            'far': ('trapmf', [50, 65, 80, 80]),
        }
        # Input2: 'change in distance' [-40 40]
        self.in2_name = 'change in distance'
        self.in2_range = (-40, 40)
        self.in2_MFs = {
            'too close': ('trapmf', [-40, -40, -20, -5]),
            'ideal': ('trimf', [-10, 0, 10]),
            'too far': ('trapmf', [5, 20, 40, 40]),
        }
        # Output1: 'speed' [0 2.93]
        self.out_name = 'speed'
        self.out_range = (0, 2.93)
        self.out_MFs = {
            'slow': ('trapmf', [0, 0, 1, 1.5]),
            'maintain': ('trimf', [1, 1.75, 2.5]),
            'fast': ('trapmf', [2, 2.5, 2.93, 2.93]),
        }

        # Fuzzy sets index to name mapping for inputs
        self.in1_MF_names = ['near', 'medium', 'far']
        self.in2_MF_names = ['too close', 'ideal', 'too far']
        self.out_MF_names = ['slow', 'maintain', 'fast']

        # Rules:
        # Format: [in1_MF_index, in2_MF_index, out_MF_index], weight=1
        # Indices are 1-based in FIS file, use 0-based here
        self.rules = [
            [0, 0, 0],  # 1 1, 1 (1) : 1
            [1, 0, 0],  # 2 1, 1 (1) : 1
            [2, 0, 2],  # 3 1, 3 (1) : 1
            [0, 1, 1],  # 1 2, 2 (1) : 1
            [1, 1, 1],  # 2 2, 2 (1) : 1
            [2, 1, 1],  # 3 2, 2 (1) : 1
            [0, 2, 2],  # 1 3, 3 (1) : 1
            [1, 2, 2],  # 2 3, 3 (1) : 1
            [2, 2, 0],  # 3 3, 1 (1) : 1
        ]

    def _mf_value(self, x, mf_type, params):
        x_arr = np.array([x], dtype=float)
        if mf_type == 'trapmf':
            return trapmf(x_arr, params)[0]
        elif mf_type == 'trimf':
            return trimf(x_arr, params)[0]
        else:
            raise ValueError("Unsupported MF type")

    def fuzzify_inputs(self, dist, delta_dist):
        # Clip inputs into their ranges first
        dist_c = np.clip(dist, self.in1_range[0], self.in1_range[1])
        delta_c = np.clip(delta_dist, self.in2_range[0], self.in2_range[1])

        # Compute membership degrees for input1
        in1_vals = []
        for name in self.in1_MF_names:
            mf_type, params = self.in1_MFs[name]
            val = self._mf_value(dist_c, mf_type, params)
            in1_vals.append(val)

        # Compute membership degrees for input2
        in2_vals = []
        for name in self.in2_MF_names:
            mf_type, params = self.in2_MFs[name]
            val = self._mf_value(delta_c, mf_type, params)
            in2_vals.append(val)

        return in1_vals, in2_vals

    def infer(self, dist, delta_dist):
        # Fuzzify inputs
        in1_vals, in2_vals = self.fuzzify_inputs(dist, delta_dist)

        # For each rule, get the firing strength: AND method 'min'
        # AndMethod='min'
        firing_strengths = []
        rule_out_indices = []
        for rule in self.rules:
            in1_idx, in2_idx, out_idx = rule
            val1 = in1_vals[in1_idx]
            val2 = in2_vals[in2_idx]
            strength = min(val1, val2)
            firing_strengths.append(strength)
            rule_out_indices.append(out_idx)

        # For output membership functions, aggregate by max of all rules firing to it
        agg = {name: 0.0 for name in self.out_MF_names}
        for strength, out_idx in zip(firing_strengths, rule_out_indices):
            name = self.out_MF_names[out_idx]
            if strength > agg[name]:
                agg[name] = strength

        # Defuzzification using centroid method over output range [0, 2.93]
        # We'll sample output range finely
        x_out = np.linspace(self.out_range[0], self.out_range[1], 1000)
        # Aggregate membership at each x using max on scaled MFs clipped by firing strength
        y_agg = np.zeros_like(x_out)
        for name, strength in agg.items():
            if strength == 0:
                continue
            mf_type, params = self.out_MFs[name]
            if mf_type == 'trapmf':
                y_mf = trapmf(x_out, params)
            elif mf_type == 'trimf':
                y_mf = trimf(x_out, params)
            else:
                raise ValueError("Unsupported MF type")
            # truncate at firing strength (ImpMethod='min')
            y_mf = np.minimum(y_mf, strength)
            y_agg = np.maximum(y_agg, y_mf)

        # centroid defuzzification
        numerator = np.sum(x_out * y_agg)
        denominator = np.sum(y_agg)
        if denominator == 0:
            # No activation, return midpoint of output range
            return (self.out_range[0] + self.out_range[1]) / 2
        centroid = numerator / denominator
        return centroid

    def compute(self, dist, delta_dist):
        """
        Compute the fuzzy controller's output speed based on:
        :param dist: distance from the person (float, 0 to 80)
        :param delta_dist: change in distance (float, -40 to 40)
        :return: speed (float, 0 to 2.93)
        """
        return self.infer(dist, delta_dist)


# Example usage
if __name__ == "__main__":
    fuzzy_controller = FuzzyForDistance()

    # Test inputs
    test_dist = 25.0        # distance from the person
    test_delta = -8.0       # change in distance

    output_speed = fuzzy_controller.compute(test_dist, test_delta)
    print(f"Input distance: {test_dist}")
    print(f"Input change in distance: {test_delta}")
    print(f"Output speed: {output_speed:.4f}")
