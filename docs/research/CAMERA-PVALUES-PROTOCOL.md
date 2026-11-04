# Protocol for testing a 35°/35° local viewing direction

This reanalysis of two existing Classic illustrations uses the brown 2 × 8 brick on PDF page 19 of 11038 and the white 2 × 4 on PDF page 8 of 11037. The angle estimates were available when the protocol was written. The middle contour thresholds, 50 and 145, are primary. The other thresholds measure sensitivity on the same source.

1. Use all seven visible body corners, the known world coordinates and pixel-aspect correction. Reserve stud positions for a separate geometric check.
2. Under the null, fix both angles of the direction from the brick center to the camera at 35°. Under the alternative, fit both angles. Optical orientation, framing and focus may vary under either hypothesis.
3. Fit seven restricted or nine unrestricted parameters to fourteen image coordinates. Compute F = ((RSS0 − RSS1)/2)/(RSS1/5). Scale, rotation and translation are solved by linear least squares inside the camera fit. Parameterizing distance by its reciprocal admits the orthographic limit in both families.
4. Simulate 1,999 independent Gaussian coordinate sets per image under the fitted null with variance RSS0/7. Use seeds 20261103 and 20261104 respectively. Refit both models to every draw. Use (1 + number of simulated F values at least as large as observed)/(1,999 + 1) for the tail estimate.
5. Retain every simulation. Check numerical convergence by increasing the optimization budget. Verify observed residuals against the original fits, Jacobian ranks, known-camera controls, F-tail integration and sensitivity to each contour threshold.
6. Report results for each image. A supplementary pooled F test assumes a common variance across independent images and has four restrictions and ten residual degrees of freedom. Shared edges, JPEG encoding and estimator bias can violate the independent-error assumption.

[Results, interpretation and replay commands](../CAMERA-PVALUES.md)
