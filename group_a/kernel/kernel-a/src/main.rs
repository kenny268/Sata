//! KERNEL-A process stub. Phase 1 starts and exits. It does not connect to a broker.

fn main() {
    let _ = std::any::type_name::<sate_a_verdict::Decision>();
    println!("kernel-a phase 1 stub; no broker connection");
}
