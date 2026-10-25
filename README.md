# FotoBot series

静态学术项目网站，目标地址为 **https://fotobot-series.github.io/**。

`index.html` 已生成，可以直接发布。访问者不需要安装 Python，也不需要服务器后端。

## 文件结构

```text
fotobot-series.github.io/
├── index.html                 # 生成好的网页，随 Git 提交
├── blog.md                    # 本仓库的正文源文件
├── .nojekyll                  # 直接发布静态文件
├── requirements.txt           # 仅用于本地生成网页
├── scripts/build.py           # Markdown → HTML；同时检查资源和章节链接
├── templates/page.html        # 页面外壳、导航和站点元信息
├── static/css/                # 旧项目的 Bulma 样式及本站样式
├── static/images/             # 视频封面和图标
├── demos/preview/             # 四个 WebM 视频
└── THIRD_PARTY_NOTICES.md      # 第三方模板和样式署名
```

## 首次上传和发布

1. 在 GitHub 创建或使用组织 **fotobot-series**。这个组织名需要可用，当前个人账号可作为组织管理员。
2. 在该组织下创建公开仓库 **fotobot-series.github.io**。创建时保持仓库为空，不额外生成 README、License 或 .gitignore。
3. 在本文件所在目录打开终端。若已经有初始提交，直接执行：

   ```powershell
   git remote add origin https://github.com/fotobot-series/fotobot-series.github.io.git
   git push -u origin main
   ```

   如果 `git log -1` 显示尚无提交，先执行下面的命令再推送：

   ```powershell
   git add .
   git commit -m "Create FotoBot series project website"
   ```

4. 在新仓库中选择 **Settings → Pages → Build and deployment**：
   - Source：**Deploy from a branch**
   - Branch：**main**
   - Folder：**/ (root)**
   - 点击 **Save**。
5. 等待 Pages 部署完成，访问 https://fotobot-series.github.io/ 。部署状态可在仓库 **Actions** 页面查看。

仓库必须属于 `fotobot-series` 组织，才能使用上述根域名。仅在个人账号下使用相同仓库名不能得到该域名。

参考：[GitHub Pages 地址规则](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[发布源设置](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 后续更新正文

推荐编辑**本仓库中的 `blog.md`**，然后在本目录运行：

```powershell
python -m pip install -r requirements.txt
python scripts/build.py
git add blog.md index.html
git commit -m "Update FotoBot series article"
git push
```

依赖只需安装一次。正文会原样呈现，不会在构建过程中自动润色。

如果仍在编辑上一层工作目录里的 `blog.md`，请显式导入最新版本：

```powershell
python scripts/build.py --source ../blog.md
```

这个命令同步更新本仓库的 `blog.md` 和 `index.html`。复制完成后，本仓库不再依赖上一层目录；请避免同时维护两个不同版本。

修改页面样式时编辑 `static/css/site.css`。修改导航、页头或域名元信息时编辑 `templates/page.html`，然后重新运行构建。

## 本地预览

在本目录运行：

```powershell
python -m http.server 8000
```

用浏览器打开 http://localhost:8000/ 。按 Ctrl+C 停止服务。

## 视频

- 四个视频是 VP8 + Opus 的 WebM 副本，保留声音；相比原始 MP4，分辨率和码率较低。
- 当前单个文件均低于 GitHub 普通仓库的 100 MiB 限制。最大的约 67 MiB，超过网页上传的 25 MiB 限制，因此请用 Git 推送。
- 原始 MP4 不包含在发布目录内，也被 `.gitignore` 排除。构建时会把视频内部的原始 MP4 备用链接改为对应 WebM，并显示可直接打开的文件链接。
- 视频使用 `preload="metadata"`，不会自动播放；封面图片来自各自视频。
- 添加新视频时，将文件放入 `demos/preview/` 并更新 `blog.md`。如需封面，可放入 `static/images/` 并在 `scripts/build.py` 的 `POSTERS` 中登记。

参考：[GitHub 文件大小限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。

## 第三方资源

页面沿用旧 LEAP 项目的静态实现方式及 Bulma 样式，未引入旧页面的菜单、轮播等脚本。署名与许可证信息见 `THIRD_PARTY_NOTICES.md`。
