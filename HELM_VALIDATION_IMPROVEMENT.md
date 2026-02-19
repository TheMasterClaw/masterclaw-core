# Helm Chart Validation CI Integration

**Date:** 2026-02-18  
**Component:** masterclaw-infrastructure  
**File Modified:** `.github/workflows/ci.yml`

## Summary

Added comprehensive Helm chart validation to the CI/CD pipeline, ensuring Kubernetes deployment manifests are validated before merging to main. This closes a gap where Helm charts could be merged with syntax errors, invalid schemas, or non-renderable templates.

## Changes Made

### 1. New CI Job: `validate-helm`

A dedicated job that runs Helm validation checks:

- **Helm Setup:** Uses `azure/setup-helm@v4` with Helm 3.14.0
- **Structure Validation:** Verifies required files exist (Chart.yaml, values.yaml, values.schema.json)
- **Helm Lint:** Runs `helm lint --strict` on the chart with all values files
- **Template Rendering:** Validates templates render correctly with test values
- **Schema Validation:** Validates values.schema.json is valid JSON with required fields
- **Kubeconform Integration:** Uses kubeconform to validate generated K8s manifests against official schemas

### 2. Updated Job Dependencies

- `validate-compose` now depends on `validate-helm`
- `build-test` now depends on `validate-helm` (in addition to existing deps)
- `ci-summary` now includes Helm validation status and requires it to pass

### 3. Enhanced Deployment Validation

Added Helm file checks to the `validate-deployment` job to ensure K8s manifests exist:
- k8s/helm/masterclaw/Chart.yaml
- k8s/helm/masterclaw/values.yaml
- k8s/helm/masterclaw/values.schema.json
- k8s/README.md

## Benefits

1. **Prevents Broken Deployments:** Catches Helm syntax errors before they reach production
2. **Schema Enforcement:** Ensures values.schema.json is valid and follows JSON Schema standards
3. **Template Validation:** Verifies Helm templates actually render without errors
4. **K8s Manifest Validation:** Uses kubeconform to validate generated manifests against K8s API schemas
5. **Early Feedback:** Developers get immediate feedback on Helm issues in PRs

## Testing

The validation runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main`
- Manual workflow dispatch

## Example Failure Scenarios Now Caught

- Missing required Helm files
- Invalid YAML syntax in values files
- Helm template rendering errors (e.g., undefined variables)
- Invalid JSON in values.schema.json
- Kubernetes manifest schema violations (e.g., invalid API versions)
- Missing required configuration values

## Integration with Existing Tools

This CI improvement complements the existing `mc k8s validate` CLI command by providing:
- Pre-merge validation (CI) vs. pre-deployment validation (CLI)
- Automated validation on every PR vs. manual validation by developers
- Kubeconform integration for deep K8s schema validation

## Future Enhancements

Potential future improvements:
- Add Helm unit tests with `helm unittest`
- Validate against multiple K8s versions
- Add cost estimation with `helm cost`
- Validate secrets are properly templated (not hardcoded)
