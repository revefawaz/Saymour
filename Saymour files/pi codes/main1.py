#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
from fuzzy_controller_dist import FuzzyForDistance  # your fuzzy logic class

# --- Constants -------------------------------------------------------
VIN_V     = 15.0    # Motor driver supply voltage (V)
MAX_SPEED = 1.40    # Max speed (m/s) at VIN_V
START_V   = 1.5     # Calibrated “just moves” voltage (V); bench-test your motors
SAMPLE_DT = 0.1     # Control loop interval (s)

# --- GPIO setup ------------------------------------------------------
GPIO.setmode(GPIO.BCM)

# Ultrasonic sensor pins
TRIG_PIN = 23
ECHO_PIN = 24
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# Motor A (Left) pins
ENA_PIN = 18   # hardware PWM
IN1_PIN = 27  # direction
IN2_PIN = 22  # direction
GPIO.setup(ENA_PIN, GPIO.OUT)
GPIO.setup(IN1_PIN, GPIO.OUT)
GPIO.setup(IN2_PIN, GPIO.OUT)

# Motor B (Right) pins
ENB_PIN = 13   # hardware PWM
IN3_PIN = 26  # direction
IN4_PIN = 19  # direction
GPIO.setup(ENB_PIN, GPIO.OUT)
GPIO.setup(IN3_PIN, GPIO.OUT)
GPIO.setup(IN4_PIN, GPIO.OUT)

# Fix forward direction for both motors
GPIO.output(IN1_PIN, GPIO.HIGH)
GPIO.output(IN2_PIN, GPIO.LOW)
GPIO.output(IN3_PIN, GPIO.HIGH)
GPIO.output(IN4_PIN, GPIO.LOW)

# Helper to read distance from HC-SR04
def read_distance(trig_pin, echo_pin):
    GPIO.output(trig_pin, False)
    time.sleep(0.05)
    GPIO.output(trig_pin, True)
    time.sleep(0.00001)
    GPIO.output(trig_pin, False)

    # wait for echo start
    while GPIO.input(echo_pin) == 0:
        pulse_start = time.time()
    # wait for echo end
    while GPIO.input(echo_pin) == 1:
        pulse_end = time.time()

    duration = pulse_end - pulse_start
    dist_cm = (duration * 34300) / 2
    # clamp to sensible range
    return max(0.0, min(dist_cm, 80.0))

def main():
    # Initialize PWM on ENA and ENB at 1 kHz
    pwm_a = GPIO.PWM(ENA_PIN, 1000)
    pwm_b = GPIO.PWM(ENB_PIN, 1000)
    pwm_a.start(0)
    pwm_b.start(0)

    # Instantiate fuzzy controller
    controller = FuzzyForDistance()

    # Prime first measurement
    prev_dist = read_distance(TRIG_PIN, ECHO_PIN)
    print(f"Initial distance: {prev_dist:.2f} cm")

    try:
        while True:
            # 1) Sense
            curr_dist = read_distance(TRIG_PIN, ECHO_PIN)
            delta     = curr_dist - prev_dist
            print(f"[Sensor] C={curr_dist:.2f} cm, Δ={delta:.2f} cm")

            # 2) Fuzzy → speed (m/s)
            speed = controller.compute(curr_dist, delta)
            print(f"[Fuzzy] speed={speed:.3f} m/s")

            # 3) Map speed → duty fraction
            if speed <= 0:
                duty_frac = 0.0
            else:
                # interpolate Vavg from START_V → VIN_V
                Vavg      = START_V + (VIN_V - START_V) * (speed / MAX_SPEED)
                duty_frac = max(0.0, min(Vavg / VIN_V, 1.0))
            duty_pct = duty_frac * 100.0
            print(f"[Map] Vavg={duty_frac*VIN_V:.2f} V → duty={duty_pct:.1f}%")

            # 4) Drive motors
            pwm_a.ChangeDutyCycle(duty_pct)
            pwm_b.ChangeDutyCycle(duty_pct)

            # shift for next loop
            prev_dist = curr_dist
            time.sleep(SAMPLE_DT)

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    finally:
        pwm_a.stop()
        pwm_b.stop()
        GPIO.cleanup()
        print("GPIO cleaned up, exiting.")

if __name__ == "__main__":
    main()
