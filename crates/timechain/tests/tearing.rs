use ::timechain::*;
use ndarray::prelude::*;

#[test]
fn test_tearing_mode() {
    let config = PlasmaConfig::new(64, 128, 20.0, 0.01);
    let mut field = EvoField::harris_sheet(config);
    let mut detector = ReconnectionDetector::new(0.005);
    let ux = Array2::zeros((64, 128));
    let uy = Array2::zeros((64, 128));
    let dt = 0.001;
    field.check_cfl(dt, 0.1).unwrap();
    for _ in 0..1000 { field.advance(dt, &ux, &uy); detector.detect(&field); }
    assert!(detector.handover_count > 0);
}
