use ::timechain::*;
use rayon::prelude::*;
use ndarray::prelude::*;

#[test]
fn test_100_nodes() {
    let config = PlasmaConfig::new(32, 32, 10.0, 0.01);
    let fields: Vec<_> = (0..100).map(|_| EvoField::harris_sheet(config)).collect();
    let handovers: Vec<u32> = fields.par_iter().map(|f| {
        let mut f = f.clone();
        let mut detector = ReconnectionDetector::new(0.005);
        let ux = Array2::zeros((32, 32));
        let uy = Array2::zeros((32, 32));
        for _ in 0..1000 { f.advance(0.001, &ux, &uy); detector.detect(&f); }
        detector.handover_count
    }).collect();
    let total: u32 = handovers.iter().sum();
    println!("Total de handovers entre 100 nós: {}", total);
    assert!(total > 0);
}
