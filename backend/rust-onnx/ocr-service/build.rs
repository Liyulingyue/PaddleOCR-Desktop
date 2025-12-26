fn main() {
    // Ensure the MSVC C++ runtime libs are available to the final link so ONNX static objects can resolve
    println!("cargo:rustc-link-search=native=E:\\Applications\\Microsoft Visual Studio\\2022\\Community\\VC\\Tools\\MSVC\\14.42.34433\\lib\\x64");
    // Try linking both debug and release variants if needed
    println!("cargo:rustc-link-lib=static=libcpmtd");
    println!("cargo:rustc-link-lib=static=libcpmt");
}
