use criterion::{criterion_group, criterion_main, Criterion};

fn dummy_bench(c: &mut Criterion) {
    c.bench_function("dummy", |b| b.iter(|| {}));
}

criterion_group!(benches, dummy_bench);
criterion_main!(benches);
