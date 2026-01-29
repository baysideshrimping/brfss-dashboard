# BRFSS Data Validation Rules

This document describes all validation checks performed by the BRFSS Data Validation Dashboard.

---

## Data Format Detection

The system automatically detects whether uploaded data is:
- **Raw Survey Data**: Individual respondent records with BRFSS variable codes
- **Aggregated Data**: Prevalence statistics by state, topic, and demographic

---

## Raw Survey Data Validation

### Required Fields

| Field | Description | Validation |
|-------|-------------|------------|
| `_STATE` | State FIPS code | Must be valid FIPS code (1-56, 66, 72, 78) |
| `_PSU` | Primary sampling unit | Must be present |

### BRFSS Variable Response Codes

#### Health Status Variables
| Variable | Description | Valid Codes |
|----------|-------------|-------------|
| `GENHLTH` | General Health | 1-5 (Excellent to Poor), 7=Don't Know, 9=Refused |
| `PHYSHLTH` | Physical Health Days | 0-30, 77=Don't Know, 88=None, 99=Refused |
| `MENTHLTH` | Mental Health Days | 0-30, 77=Don't Know, 88=None, 99=Refused |

#### Health Care Access
| Variable | Description | Valid Codes |
|----------|-------------|-------------|
| `CHECKUP1` | Last Routine Checkup | 1-5, 7=Don't Know, 8=Never, 9=Refused |
| `MEDCOST1` | Could Not See Doctor Due to Cost | 1=Yes, 2=No, 7=Don't Know, 9=Refused |

#### Chronic Conditions
| Variable | Description | Valid Codes |
|----------|-------------|-------------|
| `DIABETE4` | Diabetes Status | 1=Yes, 2=Pregnancy Only, 3=No, 4=Pre-diabetes, 7=DK, 9=Refused |
| `BPHIGH6` | High Blood Pressure | 1=Yes, 2=Pregnancy Only, 3=No, 4=Borderline, 7=DK, 9=Refused |
| `CVDINFR4` | Heart Attack | 1=Yes, 2=No, 7=Don't Know, 9=Refused |
| `CVDSTRK3` | Stroke | 1=Yes, 2=No, 7=Don't Know, 9=Refused |
| `ASTHMA3` | Ever Had Asthma | 1=Yes, 2=No, 7=Don't Know, 9=Refused |
| `CHCCOPD3` | COPD | 1=Yes, 2=No, 7=Don't Know, 9=Refused |
| `ADDEPEV3` | Depressive Disorder | 1=Yes, 2=No, 7=Don't Know, 9=Refused |

#### Tobacco Use
| Variable | Description | Valid Codes |
|----------|-------------|-------------|
| `SMOKE100` | Smoked 100+ Cigarettes | 1=Yes, 2=No, 7=Don't Know, 9=Refused |
| `SMOKDAY2` | Smoking Frequency | 1=Every Day, 2=Some Days, 3=Not at All, 7=DK, 9=Refused |

#### Cholesterol
| Variable | Description | Valid Codes |
|----------|-------------|-------------|
| `CHOLCHK3` | Cholesterol Checked | 1-6 (time ranges), 7=Don't Know, 8=Never, 9=Refused |

#### Alcohol
| Variable | Description | Valid Codes |
|----------|-------------|-------------|
| `ALCDAY4` | Alcohol Days | 101-199 (days/week), 201-299 (days/month), 777=DK, 888=None, 999=Refused |

#### Safety
| Variable | Description | Valid Codes |
|----------|-------------|-------------|
| `SEATBELT` | Seatbelt Use | 1=Always, 2=Nearly Always, 3=Sometimes, 4=Seldom, 5=Never, 7=DK, 8=Never Drive, 9=Refused |
| `EXERANY2` | Exercise in Past 30 Days | 1=Yes, 2=No, 7=Don't Know, 9=Refused |

---

## Aggregated Data Validation

### Required Fields

| Field | Validation Rule | Error if Invalid |
|-------|-----------------|------------------|
| `year` | Must be 1984 or later (BRFSS start year) | ERROR |
| `year` | Future years (>2026) | WARNING |
| `locationabbr` | Must be valid 2-letter state code | ERROR |
| `locationdesc` | Must be present (state full name) | ERROR |
| `locationdesc` | Must match locationabbr | WARNING |
| `topic` | Must be present | ERROR |
| `topic` | Must be recognized BRFSS topic | WARNING |
| `question` | Must be present | ERROR |
| `data_value` | Must be numeric | ERROR |
| `data_value` | Cannot be negative | ERROR |
| `data_value` | Cannot exceed 100% (unless Number/Rate type) | ERROR |

### Optional Field Validations

| Field | Validation Rule | Severity |
|-------|-----------------|----------|
| `sample_size` | Must be ≥ 10 | ERROR |
| `sample_size` | Warning if < 50 | WARNING |
| `sample_size` | Cannot be negative | ERROR |
| `confidence_limit_low` | Must be ≤ confidence_limit_high | ERROR |
| `confidence_limit_high` | Must be ≥ confidence_limit_low | ERROR |
| `data_value` | Must fall within confidence interval | ERROR |
| `confidence interval` | Warning if width > 30% | WARNING |
| `class` | Should be recognized category | WARNING |
| `data_value_type` | Should be recognized type | WARNING |
| `datasource` | Should be "BRFSS" | WARNING |
| `break_out_category` | Should match break_out type | WARNING |

---

## Valid State Codes

### State Abbreviations (56 valid)
```
AL, AK, AZ, AR, CA, CO, CT, DE, DC, FL, GA, HI, ID, IL, IN, IA,
KS, KY, LA, ME, MD, MA, MI, MN, MS, MO, MT, NE, NV, NH, NJ, NM,
NY, NC, ND, OH, OK, OR, PA, RI, SC, SD, TN, TX, UT, VT, VA, WA,
WV, WI, WY, PR, GU, VI, AS, MP
```

### State FIPS Codes (Raw Survey Data)
| FIPS | State | FIPS | State |
|------|-------|------|-------|
| 1 | Alabama | 30 | Montana |
| 2 | Alaska | 31 | Nebraska |
| 4 | Arizona | 32 | Nevada |
| 5 | Arkansas | 33 | New Hampshire |
| 6 | California | 34 | New Jersey |
| 8 | Colorado | 35 | New Mexico |
| 9 | Connecticut | 36 | New York |
| 10 | Delaware | 37 | North Carolina |
| 11 | District of Columbia | 38 | North Dakota |
| 12 | Florida | 39 | Ohio |
| 13 | Georgia | 40 | Oklahoma |
| 15 | Hawaii | 41 | Oregon |
| 16 | Idaho | 42 | Pennsylvania |
| 17 | Illinois | 44 | Rhode Island |
| 18 | Indiana | 45 | South Carolina |
| 19 | Iowa | 46 | South Dakota |
| 20 | Kansas | 47 | Tennessee |
| 21 | Kentucky | 48 | Texas |
| 22 | Louisiana | 49 | Utah |
| 23 | Maine | 50 | Vermont |
| 24 | Maryland | 51 | Virginia |
| 25 | Massachusetts | 53 | Washington |
| 26 | Michigan | 54 | West Virginia |
| 27 | Minnesota | 55 | Wisconsin |
| 28 | Mississippi | 56 | Wyoming |
| 29 | Missouri | | |

---

## Valid Topics (Aggregated Data)

```
Obesity, Current Smoker Status, Diabetes, Binge Drinking, Heavy Drinking,
Exercise, Physical Activity Index, Aerobic Activity, High Blood Pressure,
Cholesterol High, Cholesterol Checked, Depression, Asthma, COPD, Arthritis,
Cardiovascular Disease, Kidney, Other Cancer, Overall Health, Fair or Poor Health,
Health Care Coverage, Health Care Cost, Personal Care Provider, Last Checkup,
Flu Shot, Pneumonia Vaccination, HIV Test, E-Cigarette Use, Alcohol Consumption,
Drink and Drive, Disability status, Hearing, Healthy Days, Heart Attack, Stroke,
Coronary Heart Disease, Skin Cancer, Chronic Kidney Disease
```

---

## Validation Status Determination

| Status | Condition |
|--------|-----------|
| **PASSED** | Zero errors |
| **PASSED WITH ERRORS** | Errors present, but < 50% of rows have errors |
| **FAILED** | Errors in > 50% of rows OR missing required columns |

---

## Common Error Examples

### Raw Survey Data Errors
1. **Invalid FIPS Code**: `_STATE = 99` (no such state)
2. **Invalid Response Code**: `GENHLTH = 6` (valid is 1-5, 7, 9)
3. **Out of Range Days**: `PHYSHLTH = 45` (max is 30)
4. **Invalid Alcohol Code**: `ALCDAY4 = 350` (must be 101-199 or 201-299)

### Aggregated Data Errors
1. **Invalid State**: `locationabbr = "XX"`
2. **Negative Value**: `data_value = -5.2`
3. **Percentage Over 100**: `data_value = 125.5` (when type is Prevalence)
4. **Year Before BRFSS**: `year = 1980` (BRFSS started 1984)
5. **Sample Size Too Small**: `sample_size = 5`
6. **CI Inverted**: `confidence_limit_low = 45, confidence_limit_high = 30`
7. **Value Outside CI**: `data_value = 50, CI = [20, 40]`
8. **Missing Required Field**: Empty `topic` or `question`

---

## Data Quality Warnings (Non-Fatal)

These issues generate warnings but don't fail validation:
- Unrecognized topic (may be new or variant spelling)
- Unrecognized class category
- Small sample size (10-49)
- Wide confidence interval (> 30%)
- State name doesn't match abbreviation
- Future year in data
- Unrecognized data value type
- Unrecognized datasource

---

*Document generated for BRFSS Data Validation Dashboard Demo*
