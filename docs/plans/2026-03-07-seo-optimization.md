# SEO Optimization Plan for SmIA

## Context
SmIA 网站目前几乎没有任何 SEO 设置——缺少 meta description、OG 标签、robots.txt、sitemap.xml、结构化数据等。目标是让搜索 "smia"/"Smia"/"SmIA" 时网站出现在 Google 首位。由于 "SmIA" 是独特品牌名，做好基础 on-page SEO 即可达成目标。

**分支**: `seo-optimization` (从 `development` 创建)

## 实施步骤

### Step 1: 创建分支
- 从 `development` 创建 `seo-optimization` 分支

### Step 2: 更新 `frontend/index.html` — 静态 meta 标签
添加到 `<head>`:
- `<meta name="description">` — 描述 SmIA 功能
- Open Graph 标签: `og:title`, `og:description`, `og:type`, `og:url`, `og:image`, `og:site_name`
- Twitter Card 标签: `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`
- `<link rel="canonical" href="https://smia-agent.vercel.app/">`
- `<meta name="theme-color" content="#0a0a0a">`
- `<link rel="manifest" href="/manifest.json">`
- JSON-LD 结构化数据 (`WebApplication` schema)

### Step 3: 创建静态 SEO 文件 (frontend/public/)
- **robots.txt** — Allow `/`, `/login`, `/signup`; Disallow 所有 protected 路由和 `/api/`
- **sitemap.xml** — 列出 3 个公开页面 (`/`, `/login`, `/signup`)
- **manifest.json** — PWA 元数据 (name, short_name, icons, theme_color)

### Step 4: 创建 OG 分享图片
- 用 Playwright 截取 landing page 的 hero 区域 (3D 球体动画)
- 裁剪/调整为 1200x630 保存到 `frontend/public/og-image.png`

### Step 5: 安装 react-helmet-async + 动态页面标题
- `cd frontend && pnpm add react-helmet-async`
- 在 `frontend/src/main.tsx` 添加 `<HelmetProvider>` 包裹
- 创建 `frontend/src/components/SEO.tsx` — 可复用 SEO 组件
- 在 `Login.tsx` 和 `Signup.tsx` 中添加 `<SEO>` 组件 (Home 页使用 index.html 默认值)

### Step 6: Vercel 缓存头优化
在 `vercel.json` 的 `headers` 数组中添加:
- `/assets/(.*)` → `Cache-Control: public, max-age=31536000, immutable`
- `/(robots.txt|sitemap.xml|manifest.json)` → `Cache-Control: public, max-age=86400`

### Step 7: 部署 & 验证
- 部署到 Vercel
- 验证 `robots.txt` 和 `sitemap.xml` 可正常访问 (Vercel catch-all rewrite 不应拦截静态文件)
- 如果被拦截，在 `vercel.json` 中添加显式 rewrite 规则

### Step 8: Google Search Console (手动步骤)
用户需手动完成:
1. 访问 https://search.google.com/search-console
2. 添加 `https://smia-agent.vercel.app` 属性
3. 通过 HTML meta 标签或 DNS TXT 记录验证
4. 提交 sitemap URL
5. 请求索引首页

## 关键文件
- `frontend/index.html` — 静态 meta 标签、OG、JSON-LD
- `frontend/public/robots.txt` — 新建
- `frontend/public/sitemap.xml` — 新建
- `frontend/public/manifest.json` — 新建
- `frontend/public/og-image.png` — 新建
- `frontend/src/main.tsx` — HelmetProvider
- `frontend/src/components/SEO.tsx` — 新建
- `frontend/src/pages/Login.tsx` — 添加 SEO 组件
- `frontend/src/pages/Signup.tsx` — 添加 SEO 组件
- `vercel.json` — 缓存头

## 注意事项
- OG 图片需要手动设计或用代码生成，部署后才能被社交平台抓取
- SPA 的 SEO 依赖 Google 的 JS 渲染 (二次爬取)，静态 meta 标签确保首次爬取就有关键信息
- `react-helmet-async` 的动态标题主要影响 login/signup 页面，首页用 index.html 默认值即可

## 验证方式
1. 本地 `pnpm build` 确认构建成功
2. 部署后访问 `/robots.txt`、`/sitemap.xml` 确认返回正确内容
3. 使用 Google Rich Results Test 验证 JSON-LD
4. 使用 Facebook Sharing Debugger 验证 OG 标签
5. Google Search Console 提交 sitemap 并请求索引
