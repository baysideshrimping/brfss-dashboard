# BRFSS Dashboard Demo Cheat Sheet

Use this guide during your demo to know which files will pass/fail and what errors to expect.

---

## States That Will PASS (Green on Map)

| State | File | Why It Passes |
|-------|------|---------------|
| **Florida (FL)** | `FL_submission_2023.csv` | All data is valid - clean example |
| **Georgia (GA)** | `GA_submission_2023.csv` | All data is valid - clean example |

**Demo Tip:** Upload FL or GA first to show what a successful validation looks like.

---

## States That Will FAIL (Red on Map)

### 1. Texas (TX) - Invalid State FIPS Codes
**File:** `TX_submission_2023.csv`

**Error Type:** Invalid `_STATE` values

**What to show in CSV:**
- Rows have `_STATE = 99` (invalid - no such state)
- Rows have `_STATE = 75` (invalid - no such state)
- Valid Texas FIPS code is `48`

**Expected Errors:**
```
Row 2: Invalid state FIPS code: 99
Row 4: Invalid state FIPS code: 99
Row 6: Invalid state FIPS code: 75
Row 8: Invalid state FIPS code: 99
Row 10: Invalid state FIPS code: 75
```

---

### 2. New York (NY) - Out of Range Days Values
**File:** `NY_submission_2023.csv`

**Error Type:** `PHYSHLTH` and `MENTHLTH` values exceed 30 days

**What to show in CSV:**
- `PHYSHLTH = 45, 50, 60, 35, 42, 38` (max allowed is 30)
- `MENTHLTH = 55, 40, 45` (max allowed is 30)

**Expected Errors:**
```
Row 2: Physical Health Days: Invalid days value 45 (expected 0-30, 77, 88, or 99)
Row 3: Physical Health Days: Invalid days value 50 (expected 0-30...)
Row 4: Physical Health Days: Invalid days value 60 (expected 0-30...)
Row 7: Mental Health Days: Invalid days value 55 (expected 0-30...)
```

---

### 3. Ohio (OH) - Invalid Alcohol Codes
**File:** `OH_submission_2023.csv`

**Error Type:** `ALCDAY4` has invalid response codes

**What to show in CSV:**
- `ALCDAY4 = 350, 450, 500, 600, 750, 400` (invalid codes)
- Valid codes: 101-199 (days/week), 201-299 (days/month), 777, 888, 999

**Expected Errors:**
```
Row 2: Alcohol Days per Month: Invalid alcohol days code 350
Row 3: Alcohol Days per Month: Invalid alcohol days code 450
Row 4: Alcohol Days per Month: Invalid alcohol days code 500
Row 6: Alcohol Days per Month: Invalid alcohol days code 600
Row 8: Alcohol Days per Month: Invalid alcohol days code 750
```

---

### 4. Michigan (MI) - Non-Numeric Text Values
**File:** `MI_submission_2023.csv`

**Error Type:** Text where numbers should be

**What to show in CSV:**
- `GENHLTH = "good", "fair", "excellent", "poor"` (should be 1-5)
- `PHYSHLTH = "ten", "N/A", "#REF!"` (should be 0-30)
- `MENTHLTH = "five", "abc"` (should be 0-30)

**Expected Errors:**
```
Row 2: General Health: Non-numeric response: 'good'
Row 3: Physical Health Days: Non-numeric response: 'ten'
Row 4: Mental Health Days: Non-numeric response: 'five'
Row 5: General Health: Non-numeric response: 'fair'
Row 6: Physical Health Days: Non-numeric response: 'N/A'
Row 8: General Health: Non-numeric response: 'excellent'
Row 9: Physical Health Days: Non-numeric response: '#REF!'
```

---

### 5. Arizona (AZ) - Invalid GENHLTH Codes
**File:** `AZ_submission_2023.csv`

**Error Type:** `GENHLTH` values outside valid range

**What to show in CSV:**
- `GENHLTH = 6, 8, 0, 10` (valid codes are 1-5, 7, 9)

**Expected Errors:**
```
Row 2: General Health: Invalid response code 6 (valid: [1, 2, 3, 4, 5]...)
Row 3: General Health: Invalid response code 8 (valid: [1, 2, 3, 4, 5]...)
Row 4: General Health: Invalid response code 0 (valid: [1, 2, 3, 4, 5]...)
Row 5: General Health: Invalid response code 10 (valid: [1, 2, 3, 4, 5]...)
```

---

### 6. Nevada (NV) - Invalid Diabetes Codes
**File:** `NV_submission_2023.csv`

**Error Type:** `DIABETE4` values outside valid range

**What to show in CSV:**
- `DIABETE4 = 5, 6, 8, 10` (valid codes are 1-4, 7, 9)

**Expected Errors:**
```
Row 2: Diabetes: Invalid response code 5 (valid: [1, 2, 3, 4, 7, 9])
Row 3: Diabetes: Invalid response code 6 (valid: [1, 2, 3, 4, 7, 9])
Row 4: Diabetes: Invalid response code 8 (valid: [1, 2, 3, 4, 7, 9])
Row 6: Diabetes: Invalid response code 10 (valid: [1, 2, 3, 4, 7, 9])
```

---

### 7. Illinois (IL) - Invalid Seatbelt Codes
**File:** `IL_submission_2023.csv`

**Error Type:** `SEATBELT` values outside valid range

**What to show in CSV:**
- `SEATBELT = 10, 15, 0, 6, 20, 12, 25` (valid codes are 1-5, 7, 8, 9)

**Expected Errors:**
```
Row 2: Seatbelt Use: Invalid response code 10 (valid: [1, 2, 3, 4, 5]...)
Row 3: Seatbelt Use: Invalid response code 15 (valid: [1, 2, 3, 4, 5]...)
Row 4: Seatbelt Use: Invalid response code 0 (valid: [1, 2, 3, 4, 5]...)
Row 5: Seatbelt Use: Invalid response code 6 (valid: [1, 2, 3, 4, 5]...)
```

---

### 8. California (CA) - Mixed Errors (Pre-existing)
**File:** `CA_submission_2023.csv`

**Error Types:** Multiple error types already in file

**Errors include:**
- `GENHLTH = 8` (invalid)
- `PHYSHLTH = 45` (out of range)
- `MENTHLTH = "abc"` (non-numeric)
- `BPHIGH6 = 6` (invalid)

---

## Demo Flow Recommendation

1. **Start positive:** Upload `FL_submission_2023.csv` → Show "PASSED" status
2. **Show a clear failure:** Upload `TX_submission_2023.csv` → Invalid FIPS codes
3. **Show data entry error:** Upload `MI_submission_2023.csv` → Text in numeric fields
4. **Show range error:** Upload `NY_submission_2023.csv` → Days > 30
5. **Show the map:** Navigate to `/map` to see color-coded states
6. **Show validation document:** Reference `VALIDATION_RULES.md`

---

## Quick File Locations

All test files are in: `mock_data/state_submissions/`

To open a CSV and show the errors:
```
mock_data/state_submissions/TX_submission_2023.csv  # FIPS errors
mock_data/state_submissions/MI_submission_2023.csv  # Text errors
mock_data/state_submissions/NY_submission_2023.csv  # Range errors
mock_data/state_submissions/FL_submission_2023.csv  # Clean file
```

---

## Live Site URL

**https://brfss-dashboard.onrender.com**

(Remember: First load may take 30-50 seconds if the site has been sleeping)

---

*Prepared for Leadership Demo*
