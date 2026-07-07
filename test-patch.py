import os
import sys
from pathlib import Path

# Add project src directory to python path
current_file = Path(__file__).resolve()
sys.path.insert(0, str(current_file.parent / 'src'))

from validation.patch_validator import PatchValidator
from benchmark.patch_applier import PatchApplier

raw_response = r"""File: src/routes/auth.routes.js
<<<<<<< SEARCH
  body('password')
    .notEmpty()
    .withMessage('Password is required'),
  validateRequest
=======
  body('password')
    .isLength({ min: 8 })
    .withMessage('Password must be at least 8 characters long')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/)
    .withMessage('Password must contain at least one uppercase letter, one lowercase letter, and one number'),
  validateRequest
>>>>>>> REPLACE"""

repo_path = r"C:\Users\ajeem\Downloads\downloads\testing\testing1"
patch_payload = {
    "file": "src/routes/auth.routes.js",
    "function": "",
    "patch": raw_response
}

validator = PatchValidator(project_root=repo_path)
res = validator.validate_patch(patch_payload)
print("Validator result:", res)

# Try applying
res_apply = PatchApplier.apply_patch(repo_path, raw_response)
print("Apply result:", res_apply)
