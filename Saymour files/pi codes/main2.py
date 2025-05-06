# main2.py

import time
import RPi.GPIO as GPIO
from fuzzysteertest import FuzzyForSteering

# GPIO pins
TRIG_LEFT  = 5
ECHO_LEFT  = 6
TRIG_RIGHT = 16
ECHO_RIGHT = 20
SERVO_PIN  = 12  # must be PWM-capable

# Setup Pi pins
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for trig, echo in [(TRIG_LEFT, ECHO_LEFT), (TRIG_RIGHT, ECHO_RIGHT)]:
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
    GPIO.setup(SERVO_PIN, GPIO.OUT)

def measure_distance(trig, echo):
    GPIO.output(trig, False)
    time.sleep(0.05)

    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    start = time.time()
    while GPIO.input(echo) == 0:
        start = time.time()
    while GPIO.input(echo) == 1:
        stop = time.time()

    return ((stop - start) * 34300) / 2  # cm

def angle_to_duty(angle):
    # map -30→30° to 2%→12% duty
    a = max(-30, min(30, angle))
    return 6.5 + (a / 30) * 5

def main():
    setup_gpio()
    servo = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz for typical servo
    servo.start(6.5)                  # center at 7%

    fuzzy = FuzzyForSteering()

    try:
        while True:
            left  = measure_distance(TRIG_LEFT, ECHO_LEFT)
            right = measure_distance(TRIG_RIGHT, ECHO_RIGHT)

            angle = fuzzy.compute(left, right)
            duty  = angle_to_duty(angle)
            servo.ChangeDutyCycle(duty)

            print(f"L={left:.1f} cm R={right:.1f} cm → angle={angle:.1f}°, duty={duty:.1f}%")
            time.sleep(0.3)

    except KeyboardInterrupt:
        pass

    finally:
        servo.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
