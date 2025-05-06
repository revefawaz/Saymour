import time
import RPi.GPIO as GPIO

# -- imports for your two controllers --
from fuzzy_controller_dist import FuzzyForDistance   # adjust to your file name
from fuzzysteertest import FuzzyForSteering  # adjust to your file name

# --- GPIO pin assignments ---

# Front ultrasonic (distance controller)
TRIG_FRONT = 23
ECHO_FRONT = 24

# Left/right ultrasonics (steering controller)
TRIG_LEFT  = 5
ECHO_LEFT  = 6
TRIG_RIGHT = 16
ECHO_RIGHT = 20

# DC motor driver (L298N) pins
ENA_PIN = 18  # PWM A
IN1_PIN = 27
IN2_PIN = 22
ENB_PIN = 13  # PWM B
IN3_PIN = 26
IN4_PIN = 19

# Servo pin
SERVO_PIN = 12

# --- Helper functions ---

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    # Ultrasonic pins
    for trig, echo in [(TRIG_FRONT, ECHO_FRONT),
                       (TRIG_LEFT,  ECHO_LEFT),
                       (TRIG_RIGHT, ECHO_RIGHT)]:
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
    # Motor driver pins
    for p in [ENA_PIN, IN1_PIN, IN2_PIN, ENB_PIN, IN3_PIN, IN4_PIN]:
        GPIO.setup(p, GPIO.OUT)
    # Servo pin
    GPIO.setup(SERVO_PIN, GPIO.OUT)

def read_distance(trig, echo):
    # Trigger pulse
    GPIO.output(trig, False)
    time.sleep(0.05)
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    # Wait for echo
    start = time.time()
    while GPIO.input(echo) == 0:
        start = time.time()
    while GPIO.input(echo) == 1:
        stop = time.time()

    # Calculate distance in cm
    return ((stop - start) * 34300) / 2

def map_speed_to_duty(speed, MAX_SPEED=1.4, VIN=15.0, START_V=8.0):
    duty_frac = speed / MAX_SPEED
    MIN_FRAC = START_V / VIN
    if speed > 0 and duty_frac < MIN_FRAC:
        duty_frac = MIN_FRAC
    duty_frac = max(0.0, min(duty_frac, 1.0))
    return duty_frac * 100.0  # percent

def map_angle_to_duty(angle):
    # angle ∈ [-30,30] → duty ∈ [2,12] around center 7
    a = max(-30, min(30, angle))
    return 6.5 + (a / 30) * 5

# --- Main loop ---

def main():
    setup_gpio()

    # instantiate both fuzzy controllers
    dist_ctrl  = FuzzyForDistance()
    steer_ctrl = FuzzyForSteering()

    # PWM outputs
    pwm_a = GPIO.PWM(ENA_PIN, 1000)  # 1 kHz for motor A
    pwm_b = GPIO.PWM(ENB_PIN, 1000)  # 1 kHz for motor B
    pwm_a.start(0)
    pwm_b.start(0)

    servo = GPIO.PWM(SERVO_PIN, 50)   # 50 Hz for servo
    servo.start(6.5)                   # center

    # fix motor directions forward
    GPIO.output(IN1_PIN, GPIO.HIGH)
    GPIO.output(IN2_PIN, GPIO.LOW)
    GPIO.output(IN3_PIN, GPIO.HIGH)
    GPIO.output(IN4_PIN, GPIO.LOW)

    prev_front = read_distance(TRIG_FRONT, ECHO_FRONT)
    interval = 0.1  # 10 Hz loop

    try:
        while True:
            # 1) Read sensors
            front = read_distance(TRIG_FRONT, ECHO_FRONT)
            left  = read_distance(TRIG_LEFT,  ECHO_LEFT)
            right = read_distance(TRIG_RIGHT, ECHO_RIGHT)

            # 2) Distance controller
            delta = front - prev_front
            speed = dist_ctrl.compute(front, delta)
            duty_mot = map_speed_to_duty(speed)

            # 3) Steering controller
            angle = steer_ctrl.compute(left, right)
            duty_srv = map_angle_to_duty(angle)

            # 4) Apply outputs
            pwm_a.ChangeDutyCycle(duty_mot)
            pwm_b.ChangeDutyCycle(duty_mot)
            servo.ChangeDutyCycle(duty_srv)

            # 5) Debug
            print(f"Front: {front:.1f}cm Δ{delta:.2f}cm → speed={speed:.2f} m/s, duty={duty_mot:.1f}%")
            print(f" Left: {left:.1f}cm | Right: {right:.1f}cm → angle={angle:.1f}°, duty={duty_srv:.1f}%")
            print("––––––––––––––––––––––––––––––––––––––––")
           
            prev_front = front
            time.sleep(interval)

    except KeyboardInterrupt:
        print("Stopped by user")

    finally:
        pwm_a.stop()
        pwm_b.stop()
        servo.stop()
        GPIO.cleanup()
        print("Cleaned up GPIO")

if __name__ == "__main__":
    main()

