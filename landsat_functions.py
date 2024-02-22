import numpy as np

# Function to extract calibration coefficients
def extract_calibration_coefficients(band_number, metadata_text):
    calibration_coefficients = {}
    
    if int(band_number) < 10:
        key_mult_prefix = f"REFLECTANCE_MULT_BAND_{band_number}"
        key_add_prefix = f"REFLECTANCE_ADD_BAND_{band_number}"
    else:
        key_mult_prefix = f"RADIANCE_MULT_BAND_{band_number}"
        key_add_prefix = f"RADIANCE_ADD_BAND_{band_number}"
    
    sun_elevation = "SUN_ELEVATION"
    earth_sun_distance = "EARTH_SUN_DISTANCE"

    section_start = metadata_text.find("GROUP = LEVEL1_RADIOMETRIC_RESCALING")
    section_end = metadata_text.find("END_GROUP = LEVEL1_RADIOMETRIC_RESCALING", section_start)
    section_text = metadata_text[section_start:section_end]

    lines = section_text.split("\n")
    for line in lines:
        if key_mult_prefix in line or key_add_prefix in line:
            key, value = line.split("=")
            calibration_coefficients[key.strip()] = float(value.strip())
    
    # Extract additional coefficients from IMAGE_ATTRIBUTES
    section_start_2 = metadata_text.find("GROUP = IMAGE_ATTRIBUTES")
    section_end_2 = metadata_text.find("END_GROUP = IMAGE_ATTRIBUTES", section_start_2)
    section_text_2 = metadata_text[section_start_2:section_end_2]
    
    lines_2 = section_text_2.split("\n")
    for line in lines_2:
        if sun_elevation in line or earth_sun_distance in line:
            key, value = line.split("=")
            calibration_coefficients[key.strip()] = float(value.strip())
	
    return calibration_coefficients

# Function to extract thermal constraints for Band 10 and Band 11
def extract_thermal_constraints(band_number, metadata_text):
    k1_key = f"K1_CONSTANT_BAND_{band_number}"
    k2_key = f"K2_CONSTANT_BAND_{band_number}"

    section_start = metadata_text.find("GROUP = LEVEL1_THERMAL_CONSTANTS")
    section_end = metadata_text.find("END_GROUP = LEVEL1_THERMAL_CONSTANTS", section_start)
    section_text = metadata_text[section_start:section_end]

    k1_constant_band = None
    k2_constant_band = None

    lines = section_text.split("\n")
    for line in lines:
        if k1_key in line:
            _, k1_constant_band = line.split("=")
            k1_constant_band = float(k1_constant_band.strip())
        elif k2_key in line:
            _, k2_constant_band = line.split("=")
            k2_constant_band = float(k2_constant_band.strip())

    return k1_constant_band, k2_constant_band

# Function to convert digital numbers to radiance then brightness temperature (deg C)
def calculate_rad_bt(band_number, dn, calibration_coefficients, k1, k2):
    radiance_mult = calibration_coefficients[f"RADIANCE_MULT_BAND_{band_number}"]
    radiance_add = calibration_coefficients[f"RADIANCE_ADD_BAND_{band_number}"]
    
    radiance = (dn * radiance_mult) + radiance_add
    
    brightness_temp = k2 / (np.log((k1 / radiance) + 1)) - 273.15 # K to C
    print('Min: ', brightness_temp.min(), 'Max: ', brightness_temp.max())

    # Mask values exceeding a threshold
    masked_bt = np.ma.masked_where(brightness_temp < -100, brightness_temp)
    print('Min: ', masked_bt.min(), 'Max: ', masked_bt.max())
    
    return masked_bt

# Function to convert digital numbers to TOA reflectance
def calculate_toa_reflectance(band_number, dn, calibration_coefficients):
    reflectance_mult = calibration_coefficients[f"REFLECTANCE_MULT_BAND_{band_number}"]
    reflectance_add = calibration_coefficients[f"REFLECTANCE_ADD_BAND_{band_number}"]
    sun_elevation = calibration_coefficients["SUN_ELEVATION"]
    earth_sun_distance = calibration_coefficients["EARTH_SUN_DISTANCE"]
    
    # Calculate TOA reflectance without solar angle correction
    toa_reflectance_no_correction = dn * reflectance_mult + reflectance_add

    # Calculate TOA reflectance with solar angle correction
    theta_se = np.radians(sun_elevation)
    toa_reflectance = toa_reflectance_no_correction / np.sin(theta_se)
    masked_toa_reflectance = np.ma.masked_where(toa_reflectance < 0, toa_reflectance)

    return masked_toa_reflectance