
import RPi.GPIO as GPIO
import os

gpio_pin_number=17


GPIO.setmode(GPIO.BCM)


GPIO.setup(gpio_pin_number, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    GPIO.wait_for_edge(gpio_pin_number, GPIO.FALLING)
    #Use falling edge detection to see if pin is pulled 
    #low to avoid repeated polling
    os.system("sudo shutdown -h now")
except:
    pass

GPIO.cleanup()
