import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class FuzzyForDistance:
    def __init__(self):
        # Define the input universe and membership functions
        self.distance = ctrl.Antecedent(np.arange(0, 81, 1), 'input1')
        self.distance['near']   = fuzz.trapmf(self.distance.universe, [0, 0, 15, 30])
        self.distance['medium'] = fuzz.trimf(self.distance.universe, [20, 40, 60])
        self.distance['far']    = fuzz.trapmf(self.distance.universe, [50, 65, 80, 80])

        # Define the output universe and membership functions
        self.speed = ctrl.Consequent(np.arange(0, 1.41, 0.01), 'speed')
        self.speed['slow']     = fuzz.trapmf(self.speed.universe, [0, 0, 0.4, 0.7])
        self.speed['maintain'] = fuzz.trimf(self.speed.universe, [0.4, 0.7, 1])
        self.speed['fast']     = fuzz.trapmf(self.speed.universe, [0.7, 1, 1.4, 1.4])

        # Define the rules
        rule1 = ctrl.Rule(self.distance['near'],   self.speed['fast'])
        rule2 = ctrl.Rule(self.distance['medium'], self.speed['maintain'])
        rule3 = ctrl.Rule(self.distance['far'],    self.speed['slow'])

        # Create the control system and simulation
        speed_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
        self.sim = ctrl.ControlSystemSimulation(speed_ctrl)

    def compute(self, current_dist, delta_dist):
        """
        Compute the fuzzy output speed based on the current distance.
        delta_dist is accepted for interface compatibility but not used in rules.
        """
        # Set the fuzzy input
        self.sim.input['input1'] = current_dist
        # Perform the fuzzy computation
        self.sim.compute()
        # Return the defuzzified speed
        return self.sim.output['speed']
