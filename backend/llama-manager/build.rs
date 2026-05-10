fn main() {
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let project_root = manifest.parent().and_then(|p| p.parent()).unwrap_or(manifest);
    let llama_cpp_dir = project_root.join("third_party").join("llama.cpp");

    if !llama_cpp_dir.exists() {
        println!(
            "cargo:warning=llama.cpp submodule not found at {:?}. Set LLAMA_SERVER_PATH env or use pre-built binary.",
            llama_cpp_dir
        );
        println!("cargo:rustc-env=LLAMA_SERVER_PATH=");
        return;
    }

    let bin_dir = if cfg!(target_os = "windows") { "build/Release/bin" } else { "build/bin" };
    let server_path = llama_cpp_dir
        .join(bin_dir)
        .join(if cfg!(target_os = "windows") { "llama-server.exe" } else { "llama-server" });

    if server_path.exists() {
        println!("cargo:rustc-env=LLAMA_SERVER_PATH={}", server_path.display());
    } else {
        println!(
            "cargo:warning=llama-server not found at {:?}. Build it with: cd third_party/llama.cpp && cmake -B build && cmake --build build --config Release --target llama-server",
            server_path
        );
        println!("cargo:rustc-env=LLAMA_SERVER_PATH=");
    }
}
