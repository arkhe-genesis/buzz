use ::timechain::*;
use ndarray::prelude::*;
use ndarray_linalg::*;

#[test]
fn test_shadow_cycle() {
    let config = PlasmaConfig::new(32, 32, 10.0, 0.01);
    let mut field = EvoField::random_harris(config);
    let (u, s, vt) = field.omega_x.svd(true, true).unwrap();
    let u = u.unwrap();
    let vt = vt.unwrap();
    let shadow = Shadow::from_svd(&u, &s, &vt, 5);
    let healer = ShadowHealer::new(0.1);
    healer.heal(&mut field, &shadow);
    assert!(field.energy() > 0.0);
}
