import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class ReportGenerator:
    """测试报告生成器"""

    def __init__(self, output_dir: str = 'reports'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_pdf(self, project_name: str, test_runs: list,
                     filename: str = None) -> str:
        """生成 PDF 报告"""
        if filename is None:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        output_path = self.output_dir / filename
        doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                                 leftMargin=20*mm, rightMargin=20*mm,
                                 topMargin=20*mm, bottomMargin=20*mm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title', parent=styles['Title'],
            fontSize=18, spaceAfter=12
        )
        heading_style = ParagraphStyle(
            'Heading', parent=styles['Heading2'],
            fontSize=14, spaceAfter=8, spaceBefore=16
        )
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10)

        story = []

        story.append(Paragraph(f"兼容性测试报告: {project_name}", title_style))
        story.append(Paragraph(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 10*mm))

        # 按分辨率分组
        by_res = defaultdict(list)
        for run in test_runs:
            by_res[run.get('resolution', 'unknown')].append(run)

        story.append(Paragraph("测试结果汇总", heading_style))

        # 汇总表
        summary_data = [['分辨率', '浏览器', '状态', '差异率', '截图']]
        for run in test_runs:
            status = run.get('status', '-')
            diff = f"{run.get('diff_score', 0)*100:.1f}%" if run.get('diff_score') is not None else '-'
            summary_data.append([
                run.get('resolution', '-'),
                run.get('browser', '-'),
                status,
                diff,
                '有' if run.get('screenshot_path') else '无'
            ])

        summary_table = Table(summary_data, colWidths=[50*mm, 30*mm, 25*mm, 25*mm, 25*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10*mm))

        # 各分辨率详情
        for resolution, runs in by_res.items():
            story.append(Paragraph(f"分辨率: {resolution}", heading_style))
            res_data = [['浏览器', '状态', '差异率', '基线', '差异图']]
            for run in runs:
                status = run.get('status', '-')
                diff = f"{run.get('diff_score', 0)*100:.2f}%" if run.get('diff_score') is not None else '-'
                baseline = '有' if run.get('baseline_path') else '无'
                diff_img = '有' if run.get('diff_path') else '无'
                res_data.append([run.get('browser', '-'), status, diff, baseline, diff_img])

            res_table = Table(res_data, colWidths=[40*mm, 25*mm, 25*mm, 25*mm, 25*mm])
            res_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ]))
            story.append(res_table)
            story.append(Spacer(1, 8*mm))

        doc.build(story)
        return str(output_path)

    def generate_html_report(self, project_name: str, test_runs: list,
                             project_url: str = '', filename: str = None) -> str:
        """生成 HTML 报告"""
        if filename is None:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        output_path = self.output_dir / filename

        # 按分辨率分组
        by_res = defaultdict(list)
        for run in test_runs:
            by_res[run.get('resolution', 'unknown')].append(run)

        # 计算汇总统计
        total = len(test_runs)
        passed = sum(1 for r in test_runs if r.get('status') == 'completed')
        failed = sum(1 for r in test_runs if r.get('status') == 'failed')

        # 计算平均差异率
        diffs = [r.get('diff_score', 0) for r in test_runs if r.get('diff_score') is not None]
        avg_diff = sum(diffs) / len(diffs) * 100 if diffs else 0

        # 生成分辨率矩阵
        browsers_set = sorted(set(r.get('browser') for r in test_runs))
        resolutions_set = sorted(by_res.keys())

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>兼容性测试报告 - {project_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Noto Sans SC', 'Segoe UI', sans-serif; background: #F8FAFC; color: #1E293B; font-size: 14px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 24px; }}
  .header {{ background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; border-radius: 12px; padding: 32px; margin-bottom: 32px; }}
  .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
  .header .meta {{ opacity: 0.85; font-size: 13px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .stat-card {{ background: white; border-radius: 10px; padding: 20px; border: 1px solid #E2E8F0; }}
  .stat-card .label {{ color: #64748B; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
  .stat-card .value {{ font-size: 28px; font-weight: 700; }}
  .stat-card .value.green {{ color: #10B981; }}
  .stat-card .value.red {{ color: #EF4444; }}
  .section-title {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #1E293B; display: flex; align-items: center; gap: 8px; }}
  .res-block {{ background: white; border-radius: 10px; border: 1px solid #E2E8F0; margin-bottom: 24px; overflow: hidden; }}
  .res-block-header {{ background: #F1F5F9; padding: 14px 20px; font-weight: 600; font-size: 15px; border-bottom: 1px solid #E2E8F0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 12px 16px; text-align: center; border-bottom: 1px solid #F1F5F9; }}
  th {{ background: #F8FAFC; color: #475569; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover {{ background: #F8FAFC; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 11px; font-weight: 600; }}
  .badge-pass {{ background: #D1FAE5; color: #065F46; }}
  .badge-fail {{ background: #FEE2E2; color: #991B1B; }}
  .badge-pending {{ background: #FEF3C7; color: #92400E; }}
  .diff-bar {{ height: 6px; background: #E2E8F0; border-radius: 99px; overflow: hidden; margin-top: 4px; }}
  .diff-bar-fill {{ height: 100%; border-radius: 99px; transition: width 0.3s; }}
  .footer {{ text-align: center; color: #94A3B8; font-size: 12px; padding: 24px 0; }}
  @media (max-width: 768px) {{ .stats-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>兼容性测试报告</h1>
    <div class="meta">
      <div>项目: {project_name}</div>
      <div>URL: {project_url}</div>
      <div>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="label">测试用例</div>
      <div class="value">{total}</div>
    </div>
    <div class="stat-card">
      <div class="label">通过</div>
      <div class="value green">{passed}</div>
    </div>
    <div class="stat-card">
      <div class="label">失败</div>
      <div class="value red">{failed}</div>
    </div>
    <div class="stat-card">
      <div class="label">平均差异率</div>
      <div class="value">{avg_diff:.2f}%</div>
    </div>
  </div>
'''

        # 差异矩阵
        html += '''
  <div class="section-title">分辨率 × 浏览器 差异矩阵</div>
  <div class="res-block">
    <table>
      <thead>
        <tr>
          <th>分辨率</th>
'''
        for browser in browsers_set:
            html += f'          <th>{browser.upper()}</th>\n'
        html += '        </tr>\n      </thead>\n      <tbody>\n'

        for res in resolutions_set:
            html += f'        <tr>\n          <td><strong>{res}</strong></td>\n'
            for browser in browsers_set:
                run = next((r for r in by_res.get(res, []) if r.get('browser') == browser), None)
                if run:
                    status = run.get('status', 'pending')
                    diff = run.get('diff_score', 0)
                    badge_class = 'badge-pass' if status == 'completed' else ('badge-fail' if status == 'failed' else 'badge-pending')
                    badge_text = status.upper()
                    color = '#EF4444' if diff > 0.05 else ('#F59E0B' if diff > 0.01 else '#10B981')
                    html += f'''          <td>
            <span class="badge {badge_class}">{badge_text}</span>
            <div class="diff-bar"><div class="diff-bar-fill" style="width:{diff*100:.1f}%; background:{color};"></div></div>
            <small style="color:#64748B">{diff*100:.2f}%</small>
          </td>
'''
                else:
                    html += '          <td style="color:#CBD5E1">—</td>\n'
            html += '        </tr>\n'

        html += '      </tbody>\n    </table>\n  </div>\n'

        # 详细结果
        html += '  <div class="section-title">详细测试结果</div>\n'
        for res in resolutions_set:
            runs = by_res.get(res, [])
            html += f'''
  <div class="res-block">
    <div class="res-block-header">{res}</div>
    <table>
      <thead>
        <tr><th>浏览器</th><th>状态</th><th>差异率</th><th>基线</th><th>差异图</th></tr>
      </thead>
      <tbody>
'''
            for run in runs:
                status = run.get('status', 'pending')
                badge_class = 'badge-pass' if status == 'completed' else ('badge-fail' if status == 'failed' else 'badge-pending')
                diff = f"{run.get('diff_score', 0)*100:.2f}%" if run.get('diff_score') is not None else '-'
                baseline = '✅' if run.get('baseline_path') else '❌'
                diff_img = '✅' if run.get('diff_path') else '—'
                html += f'''        <tr>
          <td><strong>{run.get('browser', '-').upper()}</strong></td>
          <td><span class="badge {badge_class}">{status.upper()}</span></td>
          <td>{diff}</td>
          <td>{baseline}</td>
          <td>{diff_img}</td>
        </tr>
'''
            html += '      </tbody>\n    </table>\n  </div>\n'

        html += f'''
  <div class="footer">
    由自动化兼容性测试平台生成 · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  </div>
</div>
</body>
</html>'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(output_path)
