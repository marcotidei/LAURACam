# L.A.U.R.A. REMOTE Ver.2 - battery.py
import machine
from machine import Pin, ADC
import time

# Define GPIO Pins
VBAT_Read = 1  # GPIO1 for ADC Battery Read (change if needed)
ADC_Ctrl = 37  # GPIO37 for controlling ADC (if available, otherwise remove)

# Battery Voltage Calculation Constants
resolution = 12
adcMax = (2 ** resolution) - 1
adcMaxVoltage = 3.3  # Reference voltage
R1 = 390  # Voltage divider resistor
R2 = 100
measuredVoltage = 4.16
reportedVoltage = 3.9
factor = (adcMaxVoltage / adcMax) * ((R1 + R2) / float(R2)) * (measuredVoltage / reportedVoltage)

# Initialize ADC
battery_adc = machine.ADC(machine.Pin(VBAT_Read))
battery_adc.atten(machine.ADC.ATTN_11DB)  # Set attenuation for up to 3.6V

# Initialize Control Pin
adc_ctrl = machine.Pin(ADC_Ctrl, machine.Pin.OUT) if ADC_Ctrl else None

def battery_voltage():
    """Reads the battery voltage and returns it as a float."""
    if adc_ctrl:
        adc_ctrl.value(1)  # Enable ADC by setting it HIGH
        time.sleep_ms(100)  # Delay for stability

    # Read the ADC value and calculate voltage
    analog_value = battery_adc.read()
    float_voltage = factor * analog_value
    
    if adc_ctrl:
        adc_ctrl.value(1)  # Disable ADC if needed (keep it HIGH as per the V3.2 module)

    # Return the battery voltage as a float
    return float_voltage

def battery_percentage():
    """Reads the battery voltage and returns the percentage as an integer."""
    voltage = battery_voltage()  # Get the battery voltage

    # Calculate battery percentage
    max_voltage = 4.16  # Fully charged voltage
    min_voltage = 3.0  # Discharged voltage
    battery_percentage = max(0, min(100, ((voltage - min_voltage) / (max_voltage - min_voltage)) * 100))  # Ensure percentage stays between 0 and 100
    
    # Return the battery percentage as an integer
    return int(battery_percentage)

def main():
    while True:
        voltage = battery_voltage()  # Get the battery voltage
        percentage = battery_percentage()  # Get the battery percentage
        print(f"Voltage: {voltage:.3f} V, Battery Percentage: {percentage}%")
        time.sleep(5)

# Run the main loop
if __name__ == "__main__":
    main()

