# PaddleOCR-Desktop
An interface (desktop, web page, service) created for PaddleOCR

## 更新第三方库

项目使用 [Cargo](https://doc.rust-lang.org/cargo/) 管理 Rust 依赖。第三方库更新方式如下：

### 1. 工作区共享依赖（推荐）

核心依赖集中在工作区根目录的 `Cargo.toml` 中定义，成员 crate 通过 `workspace = true` 引用。例如在 `backend/rust-onnx/Cargo.toml` 中：

```toml
[workspace.dependencies]
tokio = { version = "1", features = ["full"] }
axum = "0.8"
```

成员 crate 中使用：
```toml
tokio.workspace = true
axum = { workspace = true, features = ["multipart"] }
```

这种方式只需在工作区根目录更新一次，所有成员自动生效。

### 2. 非共享依赖

部分 crate（如 `frontend/src-tauri`、`backend/llama-manager`）直接声明依赖版本。如需更新，直接修改对应 `Cargo.toml` 中的 `version` 字段即可。

### 3. 更新步骤

```bash
# 拉取最新索引
cargo update

# 更新特定依赖
cargo update -p <package-name>

# 验证编译通过
cargo check
```

### 4. 注意事项

- `ort` 使用固定版本 `=2.0.0-rc.10`，更新时需注意 ONNX 推理兼容性
- `tauri` 和 `tauri-build` 版本需保持一致
- 涉及网络请求的库（如 `reqwest`）注意 TLS 后端搭配（当前使用 `rustls-tls`）

## 初始化第三方子模块

项目使用 Git 子模块管理外部依赖库，位于 `third_party/` 目录。当前包含：

- `third_party/llama.cpp` - llama.cpp 仓库

### 初始化步骤

```bash
# 克隆仓库后初始化子模块
git submodule init
git submodule update

# 或一步完成
git clone --recursive https://github.com/your-repo/PaddleOCR-Desktop.git
```

### 更新子模块

```bash
# 进入子模块目录，拉取最新代码
cd third_party/llama.cpp
git checkout main
git pull

# 返回主仓库，提交子模块变更
cd ../..
git add third_party/llama.cpp
git commit -m "Update llama.cpp"
```

