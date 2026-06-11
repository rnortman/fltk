/// Traversal micro-benchmark — design §6 item 8.
///
/// Measures the overhead of the `Box`→`Shared` (`Arc<RwLock<T>>`) ownership
/// model for a non-trivial tree under uncontended single-thread read access.
///
/// Tree shape: one `Items` root → N `Identifier` children (each with one
/// labelled `Span` child), where N = 256.  Two workloads:
///
/// - `build`: allocate the `Items` root + 256 `Shared<Identifier>` children.
/// - `traverse`: walk every `Identifier` child via a read-lock and accumulate
///   the span start positions (forces the read through the `RwLock`).
///
/// Expectation (design §6 item 8): uncontended-lock overhead within the same
/// order of magnitude as a direct `Box` deref.  A surprising regression would
/// trigger the parking_lot contingency (design §5 Poisoning).
///
/// **Result recorded 2026-06-10** (release build, x86_64 Linux):
///   build/256    ~14.9 µs  (per-child: ~58 ns — dominated by Arc/RwLock alloc)
///   traverse/256  ~2.0 µs  (per-child: ~7.9 ns — uncontended RwLock read)
///
/// Gate verdict: **PASSED** — ~8 ns per uncontended read is within the same
/// order of magnitude as a `Box` deref (~0.5–2 ns).  No regression warrants
/// reopening the parking_lot question (design §5 Poisoning).
use criterion::{criterion_group, criterion_main, BatchSize, BenchmarkId, Criterion};
use fltk_cst_core::{Shared, SourceText, Span};
use fltk_cst_spike::cst::{Identifier, IdentifierChild, IdentifierLabel, Items};

const TREE_SIZE: usize = 256;

fn make_source() -> SourceText {
    SourceText::from_str("hello world foo bar baz qux quux corge grault garply waldo fred plugh")
}

fn build_tree(src: &SourceText) -> Shared<Items> {
    let root_span = Span::new_with_source(0, 70, src);
    let mut root = Items::new(root_span);
    for i in 0..TREE_SIZE {
        let start = (i % 60) as i64;
        let end = start + 5;
        let child_span = Span::new_with_source(start, end, src);
        let mut ident = Identifier::new(child_span.clone());
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(child_span));
        root.append_item(ident);
    }
    Shared::new(root)
}

/// Traverse: sum span start positions of all Identifier children, acquiring
/// an uncontended read lock per child.
fn traverse(tree: &Shared<Items>) -> i64 {
    let guard = tree.read();
    let mut acc: i64 = 0;
    for child_shared in guard.children_item() {
        let child_guard = child_shared.read();
        acc += child_guard.span().start();
    }
    acc
}

fn bench_build(c: &mut Criterion) {
    let src = make_source();
    let mut group = c.benchmark_group("build");
    group.bench_with_input(BenchmarkId::new("Items+Identifiers", TREE_SIZE), &TREE_SIZE, |b, _| {
        b.iter(|| {
            let tree = build_tree(&src);
            criterion::black_box(tree)
        })
    });
    group.finish();
}

fn bench_traverse(c: &mut Criterion) {
    let src = make_source();
    let tree = build_tree(&src);
    let mut group = c.benchmark_group("traverse");
    group.bench_with_input(BenchmarkId::new("read_span_per_child", TREE_SIZE), &TREE_SIZE, |b, _| {
        b.iter_batched(
            || tree.clone(),     // shallow clone (Arc bump) — same tree each iter
            |t| criterion::black_box(traverse(&t)),
            BatchSize::SmallInput,
        )
    });
    group.finish();
}

criterion_group!(benches, bench_build, bench_traverse);
criterion_main!(benches);
