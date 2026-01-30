"""
BRFSS Data Validation System
- Submit Page: Upload mock BRFSS data files
- Validation Pipeline: Validates data against CDC BRFSS format
- Dashboard: Shows validation results and errors
"""

import os
import re
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# File-based storage for submissions (survives server restarts)
SUBMISSIONS_FILE = 'submissions_data.json'
submissions = {}

def save_submissions():
    """Save submissions to JSON file for persistence."""
    try:
        with open(SUBMISSIONS_FILE, 'w') as f:
            json.dump(submissions, f)
    except Exception as e:
        print(f"Error saving submissions: {e}")

def load_submissions():
    """Load submissions from JSON file on startup."""
    global submissions
    try:
        if os.path.exists(SUBMISSIONS_FILE):
            with open(SUBMISSIONS_FILE, 'r') as f:
                submissions = json.load(f)
                print(f"Loaded {len(submissions)} submissions from file")
    except Exception as e:
        print(f"Error loading submissions: {e}")
        submissions = {}

# Load existing submissions on startup
load_submissions()

# =============================================================================
# BRFSS Data Validation Rules (based on 2023 CDC BRFSS Questionnaire)
# Supports both RAW survey responses and AGGREGATED prevalence data
# =============================================================================

# -----------------------------------------------------------------------------
# AGGREGATED DATA FIELDS (prevalence/summary statistics)
# -----------------------------------------------------------------------------

# Column name mapping: CDC format -> our internal format
# This allows us to accept real CDC data with different column naming conventions
COLUMN_NAME_MAPPING = {
    # CDC Chronic Disease Indicators format
    'stateabbr': 'locationabbr',
    'statedesc': 'locationdesc',
    'measure': 'question',
    'short_question_text': 'topic',
    'category': 'class',
    'data_value_type': 'data_value_type',
    'low_confidence_limit': 'confidence_limit_low',
    'high_confidence_limit': 'confidence_limit_high',
    'data_value_unit': 'data_value_unit',
    'populationcount': 'sample_size',
    # Also handle some variations
    'state': 'locationabbr',
    'state_abbr': 'locationabbr',
    'state_desc': 'locationdesc',
    'state_name': 'locationdesc',
    'question_text': 'question',
    'prevalence': 'data_value',
    'value': 'data_value',
    'ci_low': 'confidence_limit_low',
    'ci_high': 'confidence_limit_high',
    'conf_low': 'confidence_limit_low',
    'conf_high': 'confidence_limit_high',
}

AGGREGATED_REQUIRED_FIELDS = [
    'year',
    'locationabbr',
    'locationdesc',
    'topic',
    'question',
    'data_value'
]

AGGREGATED_OPTIONAL_FIELDS = [
    'class',
    'response',
    'break_out',
    'break_out_category',
    'sample_size',
    'confidence_limit_low',
    'confidence_limit_high',
    'data_value_unit',
    'data_value_type',
    'datasource',
    'classid',
    'topicid',
    'locationid',
    'breakoutid',
    'breakoutcategoryid',
    'questionid',
    'responseid',
    'display_order',
    'geolocation'
]

# -----------------------------------------------------------------------------
# RAW SURVEY RESPONSE FIELDS (individual respondent data)
# -----------------------------------------------------------------------------
RAW_REQUIRED_FIELDS = [
    '_state',      # State FIPS code
    '_psu',        # Primary sampling unit
]

# 2023 BRFSS Variable Names (actual data file column names)
# Maps variable names to validation rules based on the codebook
BRFSS_VARIABLE_CODES = {
    # Health Status
    'GENHLTH': {'name': 'General Health', 'responses': [1, 2, 3, 4, 5, 7, 9]},
    'PHYSHLTH': {'name': 'Physical Health Days', 'responses': 'days_0_30'},
    'MENTHLTH': {'name': 'Mental Health Days', 'responses': 'days_0_30'},
    'POORHLTH': {'name': 'Poor Health Days', 'responses': 'days_0_30'},

    # Health Care Access
    'PRIMINS1': {'name': 'Primary Insurance', 'responses': list(range(1, 11)) + [88, 77, 99]},
    'PERSDOC3': {'name': 'Personal Doctor', 'responses': [1, 2, 3, 7, 9]},
    'MEDCOST1': {'name': 'Could Not See Doctor Due to Cost', 'responses': [1, 2, 7, 9]},
    'CHECKUP1': {'name': 'Last Routine Checkup', 'responses': [1, 2, 3, 4, 5, 7, 8, 9]},

    # Exercise
    'EXERANY2': {'name': 'Exercise in Past 30 Days', 'responses': [1, 2, 7, 9]},

    # Hypertension
    'BPHIGH6': {'name': 'Ever Told High Blood Pressure', 'responses': [1, 2, 3, 4, 7, 9]},
    'BPMEDS1': {'name': 'Taking BP Medication', 'responses': [1, 2, 7, 9]},

    # Cholesterol
    'CHOLCHK3': {'name': 'Cholesterol Checked', 'responses': [1, 2, 3, 4, 5, 6, 7, 8, 9]},  # 6 = Never
    'TOLDHI3': {'name': 'Ever Told High Cholesterol', 'responses': [1, 2, 7, 9]},
    'CHOLMED3': {'name': 'Taking Cholesterol Medication', 'responses': [1, 2, 7, 9]},

    # Chronic Health Conditions
    'CVDINFR4': {'name': 'Heart Attack', 'responses': [1, 2, 7, 9]},
    'CVDCRHD4': {'name': 'Coronary Heart Disease', 'responses': [1, 2, 7, 9]},
    'CVDSTRK3': {'name': 'Stroke', 'responses': [1, 2, 7, 9]},
    'ASTHMA3': {'name': 'Ever Had Asthma', 'responses': [1, 2, 7, 9]},
    'ASTHNOW': {'name': 'Still Have Asthma', 'responses': [1, 2, 7, 9]},
    'CHCSCNC1': {'name': 'Skin Cancer', 'responses': [1, 2, 7, 9]},
    'CHCOCNC1': {'name': 'Other Cancer', 'responses': [1, 2, 7, 9]},
    'CHCCOPD3': {'name': 'COPD', 'responses': [1, 2, 7, 9]},
    'ADDEPEV3': {'name': 'Depressive Disorder', 'responses': [1, 2, 7, 9]},
    'CHCKDNY2': {'name': 'Kidney Disease', 'responses': [1, 2, 7, 9]},
    'HAVARTH4': {'name': 'Arthritis', 'responses': [1, 2, 7, 9]},
    'DIABETE4': {'name': 'Diabetes', 'responses': [1, 2, 3, 4, 7, 9]},
    'DIABAGE4': {'name': 'Diabetes Age', 'responses': 'diabetes_age'},  # Can be any age 1-97

    # Demographics
    'MARITAL': {'name': 'Marital Status', 'responses': [1, 2, 3, 4, 5, 6, 9]},
    'EDUCA': {'name': 'Education Level', 'responses': [1, 2, 3, 4, 5, 6, 9]},
    'RENTHOM1': {'name': 'Own or Rent Home', 'responses': [1, 2, 3, 7, 9]},
    'VETERAN3': {'name': 'Veteran Status', 'responses': [1, 2, 7, 9]},
    'EMPLOY1': {'name': 'Employment Status', 'responses': [1, 2, 3, 4, 5, 6, 7, 8, 9]},
    'CHILDREN': {'name': 'Number of Children', 'responses': 'count_0_87'},
    'INCOME3': {'name': 'Income Level', 'responses': list(range(1, 12)) + [77, 99]},
    'PREGNANT': {'name': 'Pregnant', 'responses': [1, 2, 7, 9]},

    # Disability
    'DEAF': {'name': 'Deaf or Hearing Difficulty', 'responses': [1, 2, 7, 9]},
    'BLIND': {'name': 'Blind or Vision Difficulty', 'responses': [1, 2, 7, 9]},
    'DECIDE': {'name': 'Difficulty Concentrating', 'responses': [1, 2, 7, 9]},
    'DIFFWALK': {'name': 'Difficulty Walking', 'responses': [1, 2, 7, 9]},
    'DIFFDRES': {'name': 'Difficulty Dressing', 'responses': [1, 2, 7, 9]},
    'DIFFALON': {'name': 'Difficulty Doing Errands', 'responses': [1, 2, 7, 9]},

    # Falls
    'FALL12MN': {'name': 'Falls in Past 12 Months', 'responses': 'count_0_76'},
    'FALLINJ5': {'name': 'Fall Injuries', 'responses': 'count_0_76'},

    # Tobacco Use
    'SMOKE100': {'name': 'Smoked 100 Cigarettes', 'responses': [1, 2, 7, 9]},
    'SMOKDAY2': {'name': 'Smoke Frequency', 'responses': [1, 2, 3, 7, 9]},
    'USENOW3': {'name': 'Smokeless Tobacco Use', 'responses': [1, 2, 3, 7, 9]},
    'ECIGNOW2': {'name': 'E-Cigarette Use', 'responses': [1, 2, 3, 4, 7, 9]},

    # Alcohol Consumption
    'ALCDAY4': {'name': 'Alcohol Days per Month', 'responses': 'alcohol_days'},
    'AVEDRNK3': {'name': 'Average Drinks per Occasion', 'responses': 'drinks'},
    'DRNK3GE5': {'name': 'Binge Drinking Days', 'responses': 'days_0_30'},
    'MAXDRNKS': {'name': 'Max Drinks on One Occasion', 'responses': 'drinks'},

    # Immunization
    'FLUSHOT7': {'name': 'Flu Shot in Past Year', 'responses': [1, 2, 7, 9]},
    'PNEUVAC4': {'name': 'Pneumonia Shot Ever', 'responses': [1, 2, 7, 9]},
    'SHINGLE2': {'name': 'Shingles Shot', 'responses': [1, 2, 7, 9]},

    # HIV/AIDS
    'HIVTST7': {'name': 'HIV Test', 'responses': [1, 2, 7, 9]},

    # Safety
    'SEATBELT': {'name': 'Seatbelt Use', 'responses': [1, 2, 3, 4, 5, 7, 8, 9]},
    'DRNKDRI2': {'name': 'Drinking and Driving', 'responses': 'count_0_76'},

    # COVID
    'COVIDPO1': {'name': 'COVID Positive Test', 'responses': [1, 2, 3, 7, 9]},
    'COVIDVA1': {'name': 'COVID Vaccine', 'responses': [1, 2, 7, 9]},
}

# Also keep questionnaire codes for backward compatibility
BRFSS_QUESTION_CODES = {
    # Section 1: Health Status
    'CHS.01': {'name': 'General Health', 'responses': [1, 2, 3, 4, 5, 7, 9]},

    # Section 2: Healthy Days
    'CHD.01': {'name': 'Physical Health Days', 'responses': 'days_0_30'},
    'CHD.02': {'name': 'Mental Health Days', 'responses': 'days_0_30'},
    'CHD.03': {'name': 'Poor Health Days', 'responses': 'days_0_30'},

    # Section 3: Health Care Access
    'CHCA.01': {'name': 'Health Insurance', 'responses': list(range(1, 11)) + [88, 77, 99]},
    'CHCA.02': {'name': 'Personal Doctor', 'responses': [1, 2, 3, 7, 9]},
    'CHCA.03': {'name': 'Could Not See Doctor Due to Cost', 'responses': [1, 2, 7, 9]},
    'CHCA.04': {'name': 'Last Routine Checkup', 'responses': [1, 2, 3, 4, 5, 7, 8, 9]},

    # Section 4: Exercise
    'CEXE.01': {'name': 'Exercise in Past 30 Days', 'responses': [1, 2, 7, 9]},

    # Section 5: Hypertension Awareness
    'CHYP.01': {'name': 'Ever Told High Blood Pressure', 'responses': [1, 2, 3, 4, 7, 9]},
    'CHYP.02': {'name': 'Taking BP Medication', 'responses': [1, 2, 7, 9]},

    # Section 6: Cholesterol Awareness
    'CCHO.01': {'name': 'Cholesterol Checked', 'responses': [1, 2, 7, 9]},
    'CCHO.02': {'name': 'Last Cholesterol Check', 'responses': [1, 2, 3, 4, 5, 7, 8, 9]},
    'CCHO.03': {'name': 'Ever Told High Cholesterol', 'responses': [1, 2, 7, 9]},
    'CCHO.04': {'name': 'Taking Cholesterol Medication', 'responses': [1, 2, 7, 9]},

    # Section 7: Chronic Health Conditions
    'CCHC.01': {'name': 'Heart Attack', 'responses': [1, 2, 7, 9]},
    'CCHC.02': {'name': 'Angina/CHD', 'responses': [1, 2, 7, 9]},
    'CCHC.03': {'name': 'Stroke', 'responses': [1, 2, 7, 9]},
    'CCHC.04': {'name': 'Asthma Ever', 'responses': [1, 2, 7, 9]},
    'CCHC.05': {'name': 'Asthma Now', 'responses': [1, 2, 7, 9]},
    'CCHC.06': {'name': 'Skin Cancer', 'responses': [1, 2, 7, 9]},
    'CCHC.07': {'name': 'Other Cancer', 'responses': [1, 2, 7, 9]},
    'CCHC.08': {'name': 'COPD', 'responses': [1, 2, 7, 9]},
    'CCHC.09': {'name': 'Depression', 'responses': [1, 2, 7, 9]},
    'CCHC.10': {'name': 'Kidney Disease', 'responses': [1, 2, 7, 9]},
    'CCHC.11': {'name': 'Arthritis', 'responses': [1, 2, 7, 9]},
    'CCHC.12': {'name': 'Diabetes', 'responses': [1, 2, 3, 4, 7, 9]},
    'CCHC.13': {'name': 'Diabetes Age', 'responses': 'age'},

    # Section 8: Demographics
    'CDEM.01': {'name': 'Age', 'responses': 'age'},
    'CDEM.02': {'name': 'Hispanic Origin', 'responses': [1, 2, 3, 4, 5, 7, 9]},
    'CDEM.03': {'name': 'Race', 'responses': [10, 20, 30, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 53, 54, 60, 77, 88, 99]},
    'CDEM.04': {'name': 'Marital Status', 'responses': [1, 2, 3, 4, 5, 6, 9]},
    'CDEM.05': {'name': 'Education', 'responses': [1, 2, 3, 4, 5, 6, 9]},
    'CDEM.06': {'name': 'Home Ownership', 'responses': [1, 2, 3, 7, 9]},
    'CDEM.07': {'name': 'County', 'responses': 'county_fips'},
    'CDEM.08': {'name': 'Zip Code', 'responses': 'zipcode'},
    'CDEM.12': {'name': 'Veteran Status', 'responses': [1, 2, 3, 4, 5, 7, 9]},
    'CDEM.13': {'name': 'Employment', 'responses': [1, 2, 3, 4, 5, 6, 7, 8, 9]},
    'CDEM.14': {'name': 'Children in Household', 'responses': 'count_0_87'},
    'CDEM.15': {'name': 'Income', 'responses': list(range(1, 12)) + [77, 99]},
    'CDEM.16': {'name': 'Weight', 'responses': 'weight'},
    'CDEM.17': {'name': 'Height Feet', 'responses': [3, 4, 5, 6, 7, 9]},
    'CDEM.18': {'name': 'Height Inches', 'responses': list(range(0, 12)) + [99]},

    # Section 9: Disability
    'CDIS.01': {'name': 'Blind', 'responses': [1, 2, 7, 9]},
    'CDIS.02': {'name': 'Difficulty Concentrating', 'responses': [1, 2, 7, 9]},
    'CDIS.03': {'name': 'Difficulty Walking', 'responses': [1, 2, 7, 9]},
    'CDIS.04': {'name': 'Difficulty Dressing', 'responses': [1, 2, 7, 9]},
    'CDIS.05': {'name': 'Difficulty Errands', 'responses': [1, 2, 7, 9]},
    'CDIS.06': {'name': 'Deaf', 'responses': [1, 2, 7, 9]},

    # Section 10: Falls
    'CFAL.01': {'name': 'Falls in Past Year', 'responses': 'count_0_76'},
    'CFAL.02': {'name': 'Fall Injuries', 'responses': 'count_0_76'},

    # Section 11: Tobacco Use
    'CTOB.01': {'name': 'Smoked 100 Cigarettes', 'responses': [1, 2, 7, 9]},
    'CTOB.02': {'name': 'Smoke Frequency', 'responses': [1, 2, 3, 7, 9]},
    'CTOB.03': {'name': 'Smokeless Tobacco', 'responses': [1, 2, 3, 7, 9]},
    'CTOB.04': {'name': 'E-Cigarette Use', 'responses': [1, 2, 3, 4, 7, 9]},

    # Section 12: Alcohol
    'CALC.01': {'name': 'Alcohol in Past 30 Days', 'responses': [1, 2, 7, 9]},
    'CALC.02': {'name': 'Days Drinking', 'responses': 'days_1_30'},
    'CALC.03': {'name': 'Drinks Per Occasion', 'responses': 'drinks'},
    'CALC.04': {'name': 'Binge Drinking Days', 'responses': 'days_0_30'},
    'CALC.05': {'name': 'Max Drinks', 'responses': 'drinks'},

    # Section 13: Immunization
    'CIMM.01': {'name': 'Flu Shot Past Year', 'responses': [1, 2, 7, 9]},
    'CIMM.02': {'name': 'Flu Shot Month', 'responses': list(range(1, 13)) + [77, 99]},
    'CIMM.03': {'name': 'Pneumonia Shot', 'responses': [1, 2, 7, 9]},
    'CIMM.04': {'name': 'Shingles Shot', 'responses': [1, 2, 7, 9]},

    # Section 14: HIV/AIDS
    'CHIV.01': {'name': 'HIV Test', 'responses': [1, 2, 7, 9]},
    'CHIV.02': {'name': 'HIV Risk', 'responses': [1, 2, 7, 9]},

    # Section 15: Seatbelt/Drinking and Driving
    'CSBD.01': {'name': 'Seatbelt Use', 'responses': [1, 2, 3, 4, 5, 7, 8, 9]},
    'CSBD.02': {'name': 'Drinking and Driving', 'responses': 'count_0_76'},
}

# State FIPS codes (used in raw survey data)
STATE_FIPS_CODES = {
    1: 'Alabama', 2: 'Alaska', 4: 'Arizona', 5: 'Arkansas',
    6: 'California', 8: 'Colorado', 9: 'Connecticut', 10: 'Delaware',
    11: 'District of Columbia', 12: 'Florida', 13: 'Georgia', 15: 'Hawaii',
    16: 'Idaho', 17: 'Illinois', 18: 'Indiana', 19: 'Iowa',
    20: 'Kansas', 21: 'Kentucky', 22: 'Louisiana', 23: 'Maine',
    24: 'Maryland', 25: 'Massachusetts', 26: 'Michigan', 27: 'Minnesota',
    28: 'Mississippi', 29: 'Missouri', 30: 'Montana', 31: 'Nebraska',
    32: 'Nevada', 33: 'New Hampshire', 34: 'New Jersey', 35: 'New Mexico',
    36: 'New York', 37: 'North Carolina', 38: 'North Dakota', 39: 'Ohio',
    40: 'Oklahoma', 41: 'Oregon', 42: 'Pennsylvania', 44: 'Rhode Island',
    45: 'South Carolina', 46: 'South Dakota', 47: 'Tennessee', 48: 'Texas',
    49: 'Utah', 50: 'Vermont', 51: 'Virginia', 53: 'Washington',
    54: 'West Virginia', 55: 'Wisconsin', 56: 'Wyoming',
    66: 'Guam', 72: 'Puerto Rico', 78: 'Virgin Islands'
}

# State abbreviation to FIPS mapping
STATE_ABBR_TO_FIPS = {
    'AL': 1, 'AK': 2, 'AZ': 4, 'AR': 5, 'CA': 6, 'CO': 8, 'CT': 9, 'DE': 10,
    'DC': 11, 'FL': 12, 'GA': 13, 'HI': 15, 'ID': 16, 'IL': 17, 'IN': 18, 'IA': 19,
    'KS': 20, 'KY': 21, 'LA': 22, 'ME': 23, 'MD': 24, 'MA': 25, 'MI': 26, 'MN': 27,
    'MS': 28, 'MO': 29, 'MT': 30, 'NE': 31, 'NV': 32, 'NH': 33, 'NJ': 34, 'NM': 35,
    'NY': 36, 'NC': 37, 'ND': 38, 'OH': 39, 'OK': 40, 'OR': 41, 'PA': 42, 'RI': 44,
    'SC': 45, 'SD': 46, 'TN': 47, 'TX': 48, 'UT': 49, 'VT': 50, 'VA': 51, 'WA': 53,
    'WV': 54, 'WI': 55, 'WY': 56, 'GU': 66, 'PR': 72, 'VI': 78
}

VALID_STATE_ABBRS = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
    'PR': 'Puerto Rico', 'GU': 'Guam', 'VI': 'Virgin Islands',
    'AS': 'American Samoa', 'MP': 'Northern Mariana Islands', 'US': 'United States'
}

# Reverse lookup for cross-validation
STATE_NAME_TO_ABBR = {v.lower(): k for k, v in VALID_STATE_ABBRS.items()}

# Valid class categories for aggregated data
VALID_CLASSES = [
    'Chronic Health Indicators', 'Health Risk Behaviors', 'Health Status',
    'Health Care Access/Coverage', 'Immunization', 'Oral Health', 'Disability',
    'Demographics', 'Tobacco Use', 'Alcohol Consumption', 'Physical Activity',
    'Nutrition', 'Overweight and Obesity', 'Cardiovascular Disease',
    'Cancer Screening', 'Mental Health', 'Injury',
    # CDC Chronic Disease Indicators categories
    'Health Outcomes', 'Unhealthy Behaviors', 'Prevention', 'Health Care',
    'Reproductive Health', 'Cross-Cutting', 'Disabilities', 'Older Adults'
]

VALID_TOPICS = [
    'Obesity', 'Current Smoker Status', 'Diabetes', 'Binge Drinking',
    'Heavy Drinking', 'Exercise', 'Physical Activity Index', 'Aerobic Activity',
    'High Blood Pressure', 'Cholesterol High', 'Cholesterol Checked',
    'Depression', 'Asthma', 'COPD', 'Arthritis', 'Cardiovascular Disease',
    'Kidney', 'Other Cancer', 'Overall Health', 'Fair or Poor Health',
    'Health Care Coverage', 'Health Care Cost', 'Personal Care Provider',
    'Last Checkup', 'Flu Shot', 'Pneumonia Vaccination', 'HIV Test',
    'E-Cigarette Use', 'Alcohol Consumption', 'Drink and Drive',
    'Disability status', 'Hearing', 'Healthy Days', 'Heart Attack', 'Stroke',
    'Coronary Heart Disease', 'Skin Cancer', 'Chronic Kidney Disease',
    'Age', 'Race', 'Education', 'Employment', 'Income',
    'Marital Status', 'Number of Children', 'BMI Categories', 'Seatbelt Use',
    # CDC Chronic Disease Indicators short question text / topics
    'Current Smoking', 'Cholesterol Screening', 'Mammography', 'Teeth Loss',
    'All Teeth Lost', 'Colorectal Cancer Screening', 'Cervical Cancer Screening',
    'Taking BP Medication', 'Physical Inactivity', 'Sleep', 'Mental Health',
    'Cancer (except skin)', 'Current Asthma', 'Lack of Health Insurance',
    'Annual Checkup', 'Routine Checkup', 'No Leisure Time Physical Activity'
]

# Lowercase lookup for case-insensitive topic matching
VALID_TOPICS_LOWER = {t.lower(): t for t in VALID_TOPICS}

VALID_RESPONSES = [
    'Yes', 'No', 'Overall', 'Male', 'Female',
    'Excellent', 'Very Good', 'Good', 'Fair', 'Poor',
    '18-24', '25-34', '35-44', '45-54', '55-64', '65+',
    'White, non-Hispanic', 'Black, non-Hispanic', 'Hispanic',
    'Asian, non-Hispanic', 'American Indian/Alaska Native',
    'Multiracial, non-Hispanic', 'Other, non-Hispanic'
]

VALID_BREAKOUTS = [
    'Overall', 'Gender', 'Age Group', 'Race/Ethnicity', 'Education', 'Income',
    'Sex', 'Age', 'Race', 'Ethnicity'
]

# Break_out_category must match break_out
VALID_BREAKOUT_CATEGORIES = {
    'Overall': ['Overall'],
    'Gender': ['Male', 'Female', 'Overall'],
    'Sex': ['Male', 'Female', 'Overall'],
    'Age Group': ['18-24', '25-34', '35-44', '45-54', '55-64', '65+', '65 or older', 'Overall'],
    'Age': ['18-24', '25-34', '35-44', '45-54', '55-64', '65+', 'Overall'],
    'Race/Ethnicity': [
        'White, non-Hispanic', 'Black, non-Hispanic', 'Hispanic',
        'Asian, non-Hispanic', 'American Indian/Alaska Native',
        'Multiracial, non-Hispanic', 'Other, non-Hispanic', 'Overall'
    ],
    'Education': [
        'Less than high school', 'High school graduate',
        'Some college or technical school', 'College graduate', 'Overall'
    ],
    'Income': [
        'Less than $15,000', '$15,000-$24,999', '$25,000-$34,999',
        '$35,000-$49,999', '$50,000+', '$75,000+', 'Overall'
    ]
}

VALID_DATA_VALUE_TYPES = [
    'Crude Prevalence', 'Age-adjusted Prevalence', 'Mean', 'Median',
    'Number', 'Percent', 'Rate', 'Weighted Frequency',
    # Lowercase variants from CDC data
    'Crude prevalence', 'Age-adjusted prevalence', 'Age-Adjusted Prevalence',
    'AgeAdjPrv', 'CrdPrv', 'Ageadjprv'
]

VALID_DATA_VALUE_UNITS = ['%', 'Number', 'Years', 'Days', 'per 100,000']

VALID_DATASOURCES = ['BRFSS', 'Behavioral Risk Factor Surveillance System']

# -----------------------------------------------------------------------------
# Response code validation helpers
# -----------------------------------------------------------------------------
STANDARD_RESPONSE_CODES = {
    'yes_no': [1, 2, 7, 9],           # 1=Yes, 2=No, 7=Don't know, 9=Refused
    'days_0_30': list(range(0, 31)) + [77, 88, 99],  # 0-30 days, 77=DK, 88=None, 99=Ref
    'days_1_30': list(range(1, 31)) + [77, 88, 99],
    'age': list(range(18, 98)) + [7, 9, 98, 99],     # 18-97, 7/9/98/99=special codes
    'count_0_76': list(range(0, 77)) + [77, 88, 99],
    'count_0_87': list(range(0, 88)) + [88, 99],
    'drinks': list(range(1, 77)) + [77, 99],
    'weight': list(range(50, 777)) + [7777, 9999],
    'county_fips': 'fips',  # 3-digit FIPS code
    'zipcode': 'zip',       # 5-digit ZIP code
}


class ValidationResult:
    """Stores validation results for a submission."""

    def __init__(self, submission_id, filename):
        self.submission_id = submission_id
        self.filename = filename
        self.timestamp = datetime.now()
        self.status = 'pending'
        self.errors = []
        self.warnings = []
        self.info = []
        self.row_count = 0
        self.valid_rows = 0
        self.data_summary = {}

    def add_error(self, row, field, message):
        self.errors.append({
            'row': row,
            'field': field,
            'message': message,
            'severity': 'error'
        })

    def add_warning(self, row, field, message):
        # Warnings are now treated as errors - everything must be correct
        self.add_error(row, field, message)

    def add_info(self, message):
        self.info.append(message)

    def to_dict(self):
        return {
            'submission_id': self.submission_id,
            'filename': self.filename,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'row_count': self.row_count,
            'valid_rows': self.valid_rows,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'data_summary': self.data_summary
        }


def detect_data_format(df):
    """
    Detect whether the data is raw survey responses or aggregated prevalence data.
    Returns 'raw', 'aggregated', or 'unknown'.
    """
    columns = set(df.columns.str.lower().str.strip())
    columns_upper = set(df.columns.str.upper().str.strip())

    # Check for raw survey data indicators
    raw_indicators = {'_state', '_psu', 'seqno', 'dispcode', 'iyear', 'imonth', 'iday'}
    has_raw = len(columns & raw_indicators) >= 2

    # Check for actual BRFSS variable names (GENHLTH, DIABETE4, SMOKE100, etc.)
    brfss_variables = {'GENHLTH', 'PHYSHLTH', 'MENTHLTH', 'DIABETE4', 'SMOKE100',
                       'BPHIGH6', 'CVDINFR4', 'ASTHMA3', 'CHECKUP1', 'EXERANY2',
                       'CHOLCHK3', 'ADDEPEV3', 'SEATBELT', 'ALCDAY4'}
    has_brfss_vars = len(columns_upper & brfss_variables) >= 3

    # Check for question code columns (CTOB01, CCHC12, etc.)
    question_pattern_cols = [c for c in columns if any(
        c.upper().startswith(prefix) for prefix in ['CTOB', 'CCHC', 'CDEM', 'CHCA', 'CHD', 'CHS']
    )]
    has_question_codes = len(question_pattern_cols) >= 3

    # Check for aggregated data indicators
    agg_indicators = {'locationabbr', 'locationdesc', 'topic', 'data_value', 'confidence_limit_low'}
    has_agg = len(columns & agg_indicators) >= 3

    if has_raw or has_question_codes or has_brfss_vars:
        return 'raw'
    elif has_agg:
        return 'aggregated'
    else:
        return 'unknown'


def validate_response_code(value, valid_responses, question_code):
    """
    Validate a response code against the valid responses for a question.
    Returns (is_valid, error_message).
    """
    if pd.isna(value) or str(value).strip() == '':
        return True, None  # Missing values are allowed (skip patterns)

    try:
        val = int(float(value))
    except (ValueError, TypeError):
        return False, f"Non-numeric response: '{value}'. Expected a number code."

    # Common BRFSS response code meanings for better error messages
    YES_NO_CODES = "1=Yes, 2=No, 7=Don't know, 9=Refused"
    HEALTH_CODES = "1=Excellent, 2=Very good, 3=Good, 4=Fair, 5=Poor, 7=Don't know, 9=Refused"

    if isinstance(valid_responses, list):
        if val not in valid_responses:
            # Provide helpful context based on response pattern
            if valid_responses == [1, 2, 7, 9]:
                hint = f"Valid codes: {YES_NO_CODES}"
            elif valid_responses == [1, 2, 3, 4, 5, 7, 9]:
                hint = f"Valid codes: {HEALTH_CODES}"
            elif valid_responses == [1, 2, 3, 4, 7, 9]:
                hint = "Valid codes: 1-4 (response options), 7=Don't know, 9=Refused"
            elif len(valid_responses) <= 10:
                hint = f"Valid codes: {valid_responses}"
            else:
                hint = f"Valid codes: {valid_responses[:8]}... (see BRFSS codebook)"
            return False, f"Invalid code {val}. {hint}"

    elif valid_responses == 'days_0_30':
        if not (0 <= val <= 30 or val in [77, 88, 99]):
            return False, f"Invalid days value {val}. Expected: 0-30 (number of days), 77=Don't know, 88=None, 99=Refused"

    elif valid_responses == 'days_1_30':
        if not (1 <= val <= 30 or val in [77, 88, 99]):
            return False, f"Invalid days value {val}. Expected: 1-30 (number of days), 77=Don't know, 88=None, 99=Refused"

    elif valid_responses == 'age':
        if not (18 <= val <= 97 or val in [7, 9, 98, 99]):
            return False, f"Invalid age {val}. Expected: 18-97 (age in years), 7=Don't know, 9=Refused, 98=Don't know/Not sure, 99=Refused"

    elif valid_responses == 'count_0_76':
        if not (0 <= val <= 76 or val in [77, 88, 99]):
            return False, f"Invalid count {val}. Expected: 0-76 (actual count), 77=Don't know, 88=None, 99=Refused"

    elif valid_responses == 'count_0_87':
        if not (0 <= val <= 87 or val in [88, 99]):
            return False, f"Invalid count {val}. Expected: 0-87 (actual count), 88=None/Don't know, 99=Refused"

    elif valid_responses == 'drinks':
        if not (1 <= val <= 76 or val in [77, 88, 99]):
            return False, f"Invalid drinks value {val}. Expected: 1-76 (number of drinks), 77=Don't know, 88=None/Don't drink, 99=Refused"

    elif valid_responses == 'diabetes_age':
        if not (1 <= val <= 97 or val in [98, 99]):
            return False, f"Invalid diabetes age {val}. Expected: 1-97 (age first diagnosed), 98=Don't know, 99=Refused"

    elif valid_responses == 'alcohol_days':
        # ALCDAY4 format: 1xx = days per week, 2xx = days per month
        if not (101 <= val <= 199 or 201 <= val <= 299 or val in [777, 888, 999]):
            return False, (f"Invalid alcohol days code {val}. Expected: 101-107 (days per week, e.g., 103=3 days/week), "
                          f"201-230 (days per month, e.g., 215=15 days/month), 777=Don't know, 888=No drinks, 999=Refused")

    return True, None


def validate_raw_survey_data(df, result):
    """
    Validate raw BRFSS survey response data.
    Recognizes both actual BRFSS variable names (GENHLTH, DIABETE4)
    and questionnaire codes (CHS.01, CCHC.12).
    """
    result.add_info("Detected format: Raw survey response data")

    # Validate _STATE (FIPS code)
    if '_state' in df.columns:
        for idx, row in df.iterrows():
            row_num = idx + 2
            state_val = row.get('_state')
            if pd.notna(state_val):
                try:
                    state_fips = int(float(state_val))
                    if state_fips not in STATE_FIPS_CODES:
                        # Suggest nearby valid codes
                        nearby = [f for f in STATE_FIPS_CODES.keys() if abs(f - state_fips) <= 5]
                        hint = f" Nearby valid codes: {nearby[:3]}" if nearby else ""
                        result.add_error(row_num, '_state',
                            f"Invalid state FIPS code: {state_fips}. Valid range is 1-56 (states), 66 (Guam), 72 (Puerto Rico), 78 (Virgin Islands).{hint}")
                except (ValueError, TypeError):
                    result.add_error(row_num, '_state',
                        f"Non-numeric state code: '{state_val}'. Expected a FIPS code number (e.g., 6 for California, 36 for New York).")

    # Build list of columns to validate
    # Check both BRFSS_VARIABLE_CODES (actual data file names) and BRFSS_QUESTION_CODES
    variable_cols = []

    for col in df.columns:
        col_upper = col.upper()

        # First check actual BRFSS variable names (GENHLTH, DIABETE4, etc.)
        if col_upper in BRFSS_VARIABLE_CODES:
            variable_cols.append((col, col_upper, BRFSS_VARIABLE_CODES[col_upper]))
            continue

        # Then check questionnaire codes (CHS.01, etc.)
        for qcode in BRFSS_QUESTION_CODES:
            normalized_qcode = qcode.replace('.', '')
            normalized_col = col_upper.replace('.', '').replace('_', '')
            if normalized_col == normalized_qcode or col_upper == qcode:
                variable_cols.append((col, qcode, BRFSS_QUESTION_CODES[qcode]))
                break

    result.add_info(f"Found {len(variable_cols)} recognized BRFSS variable columns")

    # Check for columns that might be misspelled BRFSS variables
    recognized_cols = {col.upper() for col, _, _ in variable_cols}
    system_cols = {'_STATE', '_PSU', 'SEQNO', 'IYEAR', 'IMONTH', 'IDAY', 'DISPCODE'}

    for col in df.columns:
        col_upper = col.upper()
        if col_upper in recognized_cols or col_upper in system_cols:
            continue

        # Check if column looks like a misspelled BRFSS variable
        possible_matches = []
        for var_code, var_info in BRFSS_VARIABLE_CODES.items():
            # Check for similar names (contains most of the letters)
            if len(col_upper) >= 4:
                # Simple similarity: shared characters
                shared = sum(1 for c in col_upper if c in var_code)
                if shared >= len(var_code) * 0.6 or var_code in col_upper or col_upper in var_code:
                    possible_matches.append(f"{var_code} ({var_info['name']})")

        if possible_matches:
            result.add_warning(0, col,
                f"Column '{col}' not recognized. Did you mean: {', '.join(possible_matches[:3])}?")

    # Warn if very few BRFSS columns were found
    non_system_cols = [c for c in df.columns if c.upper() not in system_cols]
    if len(variable_cols) == 0 and len(non_system_cols) > 2:
        result.add_warning(0, 'columns',
            f"No BRFSS variable columns recognized. Check column names match BRFSS codebook (e.g., GENHLTH, DIABETE4, SMOKE100).")
    elif len(variable_cols) < 3 and len(non_system_cols) > 5:
        result.add_warning(0, 'columns',
            f"Only {len(variable_cols)} BRFSS variable columns recognized out of {len(non_system_cols)} data columns. Verify column names.")

    valid_rows = 0
    for idx, row in df.iterrows():
        row_num = idx + 2
        row_valid = True

        for col_name, var_code, var_info in variable_cols:
            value = row.get(col_name)
            valid_responses = var_info.get('responses', [])

            is_valid, error_msg = validate_response_code(value, valid_responses, var_code)
            if not is_valid:
                result.add_error(row_num, col_name, f"{var_info.get('name', var_code)}: {error_msg}")
                row_valid = False

        if row_valid:
            valid_rows += 1

    result.valid_rows = valid_rows
    return result


def validate_aggregated_data(df, result):
    """
    Validate aggregated BRFSS prevalence/summary data.
    """
    result.add_info("Detected format: Aggregated prevalence data")

    # Check for required columns with helpful descriptions
    column_descriptions = {
        'year': 'Survey year (e.g., 2023)',
        'locationabbr': 'State abbreviation (e.g., TX, CA, NY)',
        'locationdesc': 'State full name (e.g., Texas, California)',
        'topic': 'Health topic category (e.g., Obesity, Diabetes, Current Smoking)',
        'question': 'Full question text describing the measure',
        'data_value': 'The prevalence value or percentage'
    }

    missing_cols = [col for col in AGGREGATED_REQUIRED_FIELDS if col not in df.columns]
    if missing_cols:
        present_cols = ', '.join(df.columns[:8].tolist())
        result.add_error(0, 'columns',
            f"Missing {len(missing_cols)} required column(s). Your file has: {present_cols}...")

        for col in missing_cols:
            desc = column_descriptions.get(col, 'Required field')
            result.add_error(0, col,
                f"Missing required column '{col}' - {desc}. Add this column to your CSV.")

        result.status = 'failed'
        return result

    # Check for recognized columns
    all_known = set(AGGREGATED_REQUIRED_FIELDS + AGGREGATED_OPTIONAL_FIELDS)
    unknown_cols = [col for col in df.columns if col not in all_known]
    if unknown_cols:
        result.add_warning(0, 'columns', f"Unknown columns: {', '.join(unknown_cols[:5])}")

    # Check for exact duplicate rows
    duplicates = df.duplicated()
    if duplicates.any():
        dup_count = duplicates.sum()
        dup_indices = df[duplicates].index.tolist()[:5]
        dup_rows = [i + 2 for i in dup_indices]  # Convert to 1-based row numbers
        result.add_error(0, 'duplicates',
            f"Found {dup_count} duplicate row(s). First duplicates at rows: {dup_rows}. Remove duplicate entries.")

    # Check for duplicate state+year+topic combinations (logical duplicates)
    if all(col in df.columns for col in ['locationabbr', 'year', 'topic']):
        key_cols = ['locationabbr', 'year', 'topic']
        if 'break_out' in df.columns:
            key_cols.append('break_out')
        if 'break_out_category' in df.columns:
            key_cols.append('break_out_category')
        logical_dups = df.duplicated(subset=key_cols, keep=False)
        if logical_dups.any():
            dup_groups = df[logical_dups].groupby(key_cols).size()
            dup_count = len(df[logical_dups])
            result.add_error(0, 'logical_duplicates',
                f"Found {dup_count} rows with duplicate state/year/topic combinations. Each combination should be unique.")

    valid_rows = 0

    for idx, row in df.iterrows():
        row_num = idx + 2
        row_valid = True

        # Validate year
        year = row.get('year')
        if pd.isna(year) or str(year).strip() == '':
            result.add_error(row_num, 'year', 'Year is required. Use a 4-digit year (e.g., 2023).')
            row_valid = False
        else:
            try:
                year_int = int(float(year))
                if year_int < 1984:
                    result.add_error(row_num, 'year',
                        f"Year {year_int} is before BRFSS started. The BRFSS survey began in 1984.")
                    row_valid = False
                elif year_int > 2026:
                    result.add_warning(row_num, 'year', f"Future year {year_int} - verify this is correct.")
            except (ValueError, TypeError):
                result.add_error(row_num, 'year',
                    f"Invalid year format: '{year}'. Expected a 4-digit year (e.g., 2023).")
                row_valid = False

        # Validate locationabbr (state abbreviation)
        loc_abbr = row.get('locationabbr')
        if pd.isna(loc_abbr) or str(loc_abbr).strip() == '':
            result.add_error(row_num, 'locationabbr',
                'State abbreviation is required. Use 2-letter state code (e.g., CA, NY, TX).')
            row_valid = False
        else:
            loc_abbr_clean = str(loc_abbr).strip().upper()
            if loc_abbr_clean not in VALID_STATE_ABBRS:
                # Suggest similar abbreviations
                similar = [a for a in VALID_STATE_ABBRS.keys() if a[0] == loc_abbr_clean[0:1]][:5]
                hint = f" States starting with '{loc_abbr_clean[0:1]}': {similar}" if similar else ""
                result.add_error(row_num, 'locationabbr',
                    f"Invalid state abbreviation: '{loc_abbr}'.{hint}")
                row_valid = False
            else:
                # Cross-validate with locationdesc
                loc_desc = row.get('locationdesc')
                if pd.notna(loc_desc) and str(loc_desc).strip():
                    expected_name = VALID_STATE_ABBRS.get(loc_abbr_clean, '').lower()
                    actual_name = str(loc_desc).strip().lower()
                    if expected_name and actual_name != expected_name:
                        result.add_warning(row_num, 'locationdesc',
                            f"State name '{loc_desc}' doesn't match abbreviation '{loc_abbr_clean}' (expected '{VALID_STATE_ABBRS.get(loc_abbr_clean)}')")

        # Validate locationdesc (state name)
        loc_desc = row.get('locationdesc')
        if pd.isna(loc_desc) or str(loc_desc).strip() == '':
            result.add_error(row_num, 'locationdesc', 'State name is required')
            row_valid = False

        # Validate class if present
        if 'class' in df.columns:
            class_val = row.get('class')
            if pd.notna(class_val) and str(class_val).strip():
                if str(class_val).strip() not in VALID_CLASSES:
                    result.add_warning(row_num, 'class', f"Unrecognized class: '{class_val}'")

        # Validate topic (case-insensitive, whitespace-tolerant)
        topic = row.get('topic')
        if pd.isna(topic) or str(topic).strip() == '':
            result.add_error(row_num, 'topic', 'Topic is required')
            row_valid = False
        else:
            topic_clean = str(topic).strip().lower()
            if topic_clean not in VALID_TOPICS_LOWER:
                # Suggest similar topics if possible
                similar = [t for t in VALID_TOPICS if topic_clean in t.lower() or t.lower() in topic_clean]
                if similar:
                    result.add_warning(row_num, 'topic',
                        f"Unrecognized topic: '{topic}'. Did you mean: {', '.join(similar[:3])}?")
                else:
                    result.add_warning(row_num, 'topic',
                        f"Unrecognized topic: '{topic}'. See BRFSS documentation for valid topics.")

        # Validate question
        question = row.get('question')
        if pd.isna(question) or str(question).strip() == '':
            result.add_error(row_num, 'question', 'Question is required')
            row_valid = False

        # Validate data_value
        data_value = row.get('data_value')
        data_val_float = None
        if pd.isna(data_value) or str(data_value).strip() == '':
            result.add_error(row_num, 'data_value',
                'Data value is required. Enter the prevalence percentage (e.g., 25.5 for 25.5%).')
            row_valid = False
        else:
            try:
                data_val_float = float(data_value)
                if data_val_float < 0:
                    result.add_error(row_num, 'data_value',
                        f"Negative value not allowed: {data_val_float}. Prevalence must be 0 or greater.")
                    row_valid = False
                elif data_val_float > 100:
                    # Check data_value_type - some types can exceed 100
                    dv_type = row.get('data_value_type', '')
                    if pd.notna(dv_type) and 'Number' in str(dv_type):
                        pass  # Numbers can exceed 100
                    elif pd.notna(dv_type) and 'Rate' in str(dv_type):
                        pass  # Rates can exceed 100
                    else:
                        result.add_error(row_num, 'data_value',
                            f"Percentage {data_val_float}% exceeds 100%. If this is a count or rate, set data_value_type to 'Number' or 'Rate'.")
                        row_valid = False
            except (ValueError, TypeError):
                result.add_error(row_num, 'data_value',
                    f"Invalid numeric value: '{data_value}'. Expected a number (e.g., 25.5).")
                row_valid = False

        # Validate sample_size if present
        if 'sample_size' in df.columns:
            sample = row.get('sample_size')
            if pd.notna(sample) and str(sample).strip() != '':
                try:
                    sample_int = int(float(sample))
                    if sample_int < 0:
                        result.add_error(row_num, 'sample_size',
                            f"Negative sample size: {sample_int}. Sample size must be a positive integer.")
                        row_valid = False
                    elif sample_int < 10:
                        result.add_error(row_num, 'sample_size',
                            f"Sample size {sample_int} is too small for reliable estimates. BRFSS typically requires n >= 10.")
                        row_valid = False
                    elif sample_int < 50:
                        result.add_warning(row_num, 'sample_size',
                            f"Small sample size (n={sample_int}) may produce wide confidence intervals. Consider if estimate is reliable.")
                except (ValueError, TypeError):
                    result.add_error(row_num, 'sample_size',
                        f"Invalid sample size: '{sample}'. Expected a positive integer.")
                    row_valid = False

        # Validate confidence limits
        if 'confidence_limit_low' in df.columns and 'confidence_limit_high' in df.columns:
            cl_low = row.get('confidence_limit_low')
            cl_high = row.get('confidence_limit_high')
            if pd.notna(cl_low) and pd.notna(cl_high):
                try:
                    low = float(cl_low)
                    high = float(cl_high)

                    # Check for negative confidence limits (invalid for prevalence)
                    if low < 0:
                        result.add_error(row_num, 'confidence_limit_low',
                            f"Negative confidence limit: {low}. Prevalence CI bounds must be >= 0.")
                        row_valid = False
                    if high < 0:
                        result.add_error(row_num, 'confidence_limit_high',
                            f"Negative confidence limit: {high}. Prevalence CI bounds must be >= 0.")
                        row_valid = False

                    # Check for CI bounds exceeding 100% (for prevalence data)
                    dv_type = row.get('data_value_type', '')
                    is_prevalence = pd.isna(dv_type) or 'Prevalence' in str(dv_type) or '%' in str(row.get('data_value_unit', ''))
                    if is_prevalence and high > 100:
                        result.add_error(row_num, 'confidence_limit_high',
                            f"CI upper bound ({high}%) exceeds 100%. Prevalence cannot exceed 100%.")
                        row_valid = False

                    if low > high:
                        result.add_error(row_num, 'confidence_limit',
                            f"Confidence limits are inverted: low ({low}) > high ({high}). Swap the values or verify source data.")
                        row_valid = False
                    # Validate that data_value is within CI
                    if data_val_float is not None:
                        if data_val_float < low or data_val_float > high:
                            result.add_error(row_num, 'confidence_limit',
                                f"Data value ({data_val_float}%) is outside its confidence interval [{low}, {high}]. "
                                f"The point estimate should fall within the CI bounds.")
                            row_valid = False
                        # Check for suspiciously wide CI
                        ci_width = high - low
                        if ci_width > 30:
                            result.add_warning(row_num, 'confidence_limit',
                                f"Wide confidence interval ({ci_width:.1f} percentage points). "
                                f"This may indicate small sample size or high variability.")
                except (ValueError, TypeError):
                    result.add_error(row_num, 'confidence_limit',
                        f"Invalid confidence limit values. Expected numeric values.")

        # Validate break_out and break_out_category consistency
        if 'break_out' in df.columns and 'break_out_category' in df.columns:
            break_out = row.get('break_out')
            break_out_cat = row.get('break_out_category')
            if pd.notna(break_out) and pd.notna(break_out_cat):
                break_out_str = str(break_out).strip()
                break_out_cat_str = str(break_out_cat).strip()
                if break_out_str in VALID_BREAKOUT_CATEGORIES:
                    valid_cats = VALID_BREAKOUT_CATEGORIES[break_out_str]
                    if break_out_cat_str not in valid_cats:
                        result.add_warning(row_num, 'break_out_category',
                            f"Category '{break_out_cat_str}' may not be valid for break_out '{break_out_str}'")

        # Validate data_value_type
        if 'data_value_type' in df.columns:
            dv_type = row.get('data_value_type')
            if pd.notna(dv_type) and str(dv_type).strip():
                if str(dv_type).strip() not in VALID_DATA_VALUE_TYPES:
                    result.add_warning(row_num, 'data_value_type', f"Unrecognized data value type: '{dv_type}'")

        # Validate datasource
        if 'datasource' in df.columns:
            datasource = row.get('datasource')
            if pd.notna(datasource) and str(datasource).strip():
                if str(datasource).strip() not in VALID_DATASOURCES:
                    result.add_warning(row_num, 'datasource', f"Unrecognized datasource: '{datasource}'")

        # Validate data_value_unit
        if 'data_value_unit' in df.columns:
            dv_unit = row.get('data_value_unit')
            if pd.notna(dv_unit) and str(dv_unit).strip():
                valid_units = ['%', 'per 100,000', 'per 1,000', 'Number', 'Years', 'Days']
                if str(dv_unit).strip() not in valid_units:
                    result.add_error(row_num, 'data_value_unit',
                        f"Unrecognized data value unit: '{dv_unit}'. Expected one of: {', '.join(valid_units)}")
                    row_valid = False

        # Validate response column
        if 'response' in df.columns:
            response = row.get('response')
            if pd.notna(response) and str(response).strip():
                valid_responses = ['Yes', 'No', 'yes', 'no', 'YES', 'NO']
                if str(response).strip() not in valid_responses:
                    result.add_error(row_num, 'response',
                        f"Invalid response value: '{response}'. Expected 'Yes' or 'No'.")
                    row_valid = False

        # Check for leading/trailing whitespace in key fields
        for field in ['locationabbr', 'topic', 'question']:
            if field in df.columns:
                val = row.get(field)
                if pd.notna(val):
                    val_str = str(val)
                    if val_str != val_str.strip():
                        result.add_error(row_num, field,
                            f"Field '{field}' has leading or trailing whitespace: '{val_str}'. Remove extra spaces.")
                        row_valid = False

        # Check for special/non-printable characters in text fields
        for field in ['locationdesc', 'topic', 'question']:
            if field in df.columns:
                val = row.get(field)
                if pd.notna(val):
                    val_str = str(val)
                    # Check for non-printable characters (except common ones)
                    if any(ord(c) < 32 and c not in '\t\n\r' for c in val_str):
                        result.add_error(row_num, field,
                            f"Field '{field}' contains non-printable characters. Check for data corruption.")
                        row_valid = False

        if row_valid:
            valid_rows += 1

    result.valid_rows = valid_rows
    return result


def validate_brfss_data(df, result):
    """
    Validate BRFSS data against CDC format rules.
    Auto-detects whether data is raw survey responses or aggregated prevalence data.
    """
    result.row_count = len(df)
    result.status = 'processing'

    # Normalize column names (lowercase, strip whitespace, remove underscores for matching)
    df.columns = df.columns.str.lower().str.strip()

    # Apply column name mapping to support various CDC data formats
    # BUT skip columns starting with underscore (like _state, _psu) - those are raw BRFSS fields
    rename_map = {}
    for col in df.columns:
        # Skip raw BRFSS columns that start with underscore
        if col.startswith('_'):
            continue
        # Remove underscores for matching
        col_normalized = col.replace('_', '')
        if col_normalized in COLUMN_NAME_MAPPING:
            rename_map[col] = COLUMN_NAME_MAPPING[col_normalized]
        elif col in COLUMN_NAME_MAPPING:
            rename_map[col] = COLUMN_NAME_MAPPING[col]

    if rename_map:
        df.rename(columns=rename_map, inplace=True)
        result.add_info(f"Mapped {len(rename_map)} column names to standard format")

    result.add_info(f"File contains {len(df)} rows and {len(df.columns)} columns")

    # Detect data format
    data_format = detect_data_format(df)

    if data_format == 'raw':
        validate_raw_survey_data(df, result)
    elif data_format == 'aggregated':
        validate_aggregated_data(df, result)
    else:
        # Try aggregated format by default, fall back to basic validation
        result.add_warning(0, 'format', "Could not determine data format, attempting aggregated data validation")
        validate_aggregated_data(df, result)

    # Generate summary statistics
    if 'locationabbr' in df.columns:
        result.data_summary = {
            'format': data_format,
            'states': df['locationabbr'].nunique() if 'locationabbr' in df.columns else 0,
            'topics': df['topic'].nunique() if 'topic' in df.columns else 0,
            'years': sorted([int(y) for y in df['year'].dropna().unique()]) if 'year' in df.columns else [],
            'topics_list': df['topic'].dropna().unique().tolist()[:10] if 'topic' in df.columns else []
        }
    elif '_state' in df.columns:
        unique_states = df['_state'].dropna().unique()
        state_names = [STATE_FIPS_CODES.get(int(s), f'Unknown({s})') for s in unique_states if pd.notna(s)]
        result.data_summary = {
            'format': data_format,
            'states': len(unique_states),
            'state_names': state_names[:10],
            'respondents': len(df)
        }
    else:
        result.data_summary = {'format': data_format}

    # Determine final status - simple pass/fail
    if len(result.errors) == 0:
        result.status = 'passed'
        result.add_info("All validation checks passed!")
    else:
        result.status = 'failed'
        result.add_info(f"Validation failed: {len(result.errors)} error(s)")

    return result


@app.route('/')
def index():
    """Redirect to submit page."""
    return redirect(url_for('submit'))


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    """File submission page."""
    message = None
    error = None

    if request.method == 'POST':
        if 'file' not in request.files:
            error = 'No file selected'
        else:
            file = request.files['file']
            if file.filename == '':
                error = 'No file selected'
            elif file.filename.endswith(('.xlsx', '.xls')):
                error = 'Excel files (.xlsx/.xls) are not supported. Please export your data as CSV first (File → Save As → CSV).'
            elif not file.filename.endswith(('.csv', '.json')):
                error = 'Only CSV and JSON files are supported. Please convert your file to CSV format.'
            else:
                # Generate unique submission ID
                submission_id = str(uuid.uuid4())[:8]

                # Save file
                filename = f"{submission_id}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)

                # Create validation result
                result = ValidationResult(submission_id, file.filename)

                # Check filename convention (warning only)
                filename_pattern = r'^[A-Z]{2}_submission_\d{4}\.csv$'
                if not re.match(filename_pattern, file.filename):
                    result.add_warning(0, 'filename',
                        f"Filename '{file.filename}' doesn't match expected pattern: STATE_submission_YEAR.csv (e.g., TX_submission_2023.csv)")

                # Load and validate data
                try:
                    if file.filename.endswith('.csv'):
                        df = pd.read_csv(filepath)
                    else:
                        df = pd.read_json(filepath)

                    # Check for empty file
                    if len(df) == 0:
                        result.status = 'failed'
                        result.add_error(0, 'file', 'File is empty. Please upload a file with data rows.')
                    elif len(df) < 5:
                        result.add_warning(0, 'file', f'File contains only {len(df)} rows. BRFSS submissions typically contain more data.')
                        validate_brfss_data(df, result)
                    else:
                        validate_brfss_data(df, result)

                except Exception as e:
                    result.status = 'failed'
                    result.add_error(0, 'file', f'Failed to parse file: {str(e)}')

                # Store result and save to file
                submissions[submission_id] = result.to_dict()
                save_submissions()

                message = f"File submitted successfully! Submission ID: {submission_id}"
                return redirect(url_for('validation_detail', submission_id=submission_id))

    return render_template('submit.html', message=message, error=error)


@app.route('/validation')
def validation_dashboard():
    """Validation results dashboard."""
    total = len(submissions)
    passed = sum(1 for s in submissions.values() if s['status'] == 'passed')
    failed = sum(1 for s in submissions.values() if s['status'] == 'failed')

    total_errors = sum(s['error_count'] for s in submissions.values())

    summary = {
        'total_submissions': total,
        'passed': passed,
        'failed': failed,
        'total_errors': total_errors,
        'pass_rate': round(passed / total * 100, 1) if total > 0 else 0
    }

    recent = sorted(
        submissions.values(),
        key=lambda x: x['timestamp'],
        reverse=True
    )[:20]

    error_types = {}
    for sub in submissions.values():
        for err in sub['errors']:
            field = err['field']
            error_types[field] = error_types.get(field, 0) + 1

    return render_template(
        'validation_dashboard.html',
        summary=summary,
        submissions=recent,
        error_types=error_types
    )


@app.route('/validation/<submission_id>')
def validation_detail(submission_id):
    """Detailed validation results for a submission."""
    if submission_id not in submissions:
        return render_template('error.html', message='Submission not found'), 404

    result = submissions[submission_id]
    return render_template('validation_detail.html', result=result)


@app.route('/api/submissions')
def api_submissions():
    """API endpoint for submissions data."""
    return jsonify(list(submissions.values()))


@app.route('/api/submit', methods=['POST'])
def api_submit():
    """API endpoint for file submission."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check for Excel files
    if file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Excel files (.xlsx/.xls) are not supported. Please export your data as CSV first.'}), 400

    # Check for supported file types
    if not file.filename.endswith(('.csv', '.json')):
        return jsonify({'error': 'Only CSV and JSON files are supported.'}), 400

    submission_id = str(uuid.uuid4())[:8]
    filename = f"{submission_id}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    result = ValidationResult(submission_id, file.filename)

    # Check filename convention (warning only)
    filename_pattern = r'^[A-Z]{2}_submission_\d{4}\.csv$'
    if not re.match(filename_pattern, file.filename):
        result.add_warning(0, 'filename',
            f"Filename '{file.filename}' doesn't match expected pattern: STATE_submission_YEAR.csv (e.g., TX_submission_2023.csv)")

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_json(filepath)

        # Check for empty file
        if len(df) == 0:
            result.status = 'failed'
            result.add_error(0, 'file', 'File is empty. Please upload a file with data rows.')
        elif len(df) < 5:
            result.add_warning(0, 'file', f'File contains only {len(df)} rows. BRFSS submissions typically contain more data.')
            validate_brfss_data(df, result)
        else:
            validate_brfss_data(df, result)
    except Exception as e:
        result.status = 'failed'
        result.add_error(0, 'file', f'Failed to parse file: {str(e)}')

    submissions[submission_id] = result.to_dict()
    save_submissions()

    return jsonify(result.to_dict())


@app.route('/api/clear', methods=['POST'])
def api_clear():
    """Clear all submissions data. Requires password."""
    CLEAR_PASSWORD = "brfss2024"  # Simple password for demo

    data = request.get_json() or {}
    password = data.get('password', '')

    if password != CLEAR_PASSWORD:
        return jsonify({'error': 'Invalid password'}), 401

    submissions.clear()
    save_submissions()
    return jsonify({'status': 'cleared', 'message': 'All submissions have been cleared'})


@app.route('/map')
def state_map():
    """Interactive US map showing validation status by state."""
    # Build state status from submissions
    state_status = {}
    state_details = {}

    for sub in submissions.values():
        # Extract state from submission
        state_fips = None
        state_abbr = None

        # Check data_summary for state info
        summary = sub.get('data_summary', {})

        # Try to get state from the submission filename or data
        filename = sub.get('filename', '')
        if '_submission' in filename:
            # Extract state abbr from filename like "GA_submission_2023.csv"
            state_abbr = filename.split('_')[0].upper()

        # Map FIPS to abbreviation for raw data
        if 'state_names' in summary and summary['state_names']:
            # Get first state name and map to abbreviation
            state_name = summary['state_names'][0] if summary['state_names'] else None
            if state_name:
                for abbr, name in VALID_STATE_ABBRS.items():
                    if name == state_name:
                        state_abbr = abbr
                        break

        if state_abbr:
            status = sub.get('status', 'unknown')
            error_count = sub.get('error_count', 0)
            row_count = sub.get('row_count', 0)
            valid_rows = sub.get('valid_rows', 0)

            state_status[state_abbr] = status
            state_details[state_abbr] = {
                'status': status,
                'errors': error_count,
                'rows': row_count,
                'valid': valid_rows,
                'filename': filename,
                'timestamp': sub.get('timestamp', '')
            }

    return render_template('map.html',
                         state_status=state_status,
                         state_details=state_details,
                         total_states=len(state_status),
                         passed=sum(1 for s in state_status.values() if s == 'passed'),
                         failed=sum(1 for s in state_status.values() if s == 'failed'))


@app.route('/api/state-status')
def api_state_status():
    """API endpoint for state validation status."""
    state_status = {}

    for sub in submissions.values():
        summary = sub.get('data_summary', {})
        filename = sub.get('filename', '')

        state_abbr = None
        if '_submission' in filename:
            state_abbr = filename.split('_')[0].upper()

        if 'state_names' in summary and summary['state_names']:
            state_name = summary['state_names'][0]
            for abbr, name in VALID_STATE_ABBRS.items():
                if name == state_name:
                    state_abbr = abbr
                    break

        if state_abbr:
            state_status[state_abbr] = {
                'status': sub.get('status', 'unknown'),
                'errors': sub.get('error_count', 0),
                'rows': sub.get('row_count', 0),
                'valid': sub.get('valid_rows', 0),
                'submission_id': sub.get('submission_id', ''),
                'timestamp': sub.get('timestamp', '')
            }

    return jsonify(state_status)


if __name__ == '__main__':
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("=" * 50)
    print("BRFSS Data Validation System")
    print("=" * 50)
    print("Access the app at:")
    print(f"  - Local:      http://127.0.0.1:5000/submit")
    print(f"  - Network:    http://{local_ip}:5000/submit")
    print("  - Validation: http://127.0.0.1:5000/validation")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
