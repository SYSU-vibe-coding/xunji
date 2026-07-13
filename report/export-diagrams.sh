#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${ROOT_DIR}/diagram-previews"
TEMP_DIR="$(mktemp -d /tmp/xunji-report-diagrams.XXXXXX)"

cleanup() {
  rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

mkdir -p "${OUTPUT_DIR}"
cp -R "${ROOT_DIR}/_template" "${TEMP_DIR}/_template"

extract_diagram() {
  local source_file="$1"
  local diagram_index="$2"

  awk -v target="${diagram_index}" '
    index($0, "\\begin{tikzpicture}") {
      count++
      if (count == target) {
        capture = 1
      }
    }
    capture && index($0, "\\end{tikzpicture}") {
      print "\\end{tikzpicture}"
      exit
    }
    capture { print }
  ' "${source_file}" > "${TEMP_DIR}/diagram-body.tex"

  if [[ ! -s "${TEMP_DIR}/diagram-body.tex" ]]; then
    echo "[diagram] no TikZ diagram ${diagram_index} in ${source_file}" >&2
    return 1
  fi
}

render_diagram() {
  local report_dir="$1"
  local diagram_index="$2"
  local output_name="$3"
  local source_file="${ROOT_DIR}/${report_dir}/content.tex"

  echo "[diagram] exporting ${output_name}.png"
  extract_diagram "${source_file}" "${diagram_index}"

  {
    printf '%s\n' '\documentclass[a4paper,12pt]{article}'
    printf '%s\n' '\newcommand{\ReportTitle}{图形预览}'
    printf '%s\n' '\newcommand{\ProjectName}{寻迹校园失物招领平台}'
    printf '%s\n' '\input{_template/setup/package.tex}'
    printf '%s\n' '\input{_template/setup/format.tex}'
    printf '%s\n' '\usepackage[active,tightpage]{preview}'
    printf '%s\n' '\setlength{\PreviewBorder}{10pt}'
    printf '%s\n' '\tikzset{'
    printf '%s\n' '  umlclass/.style={rectangle split,rectangle split parts=2,draw=reportblue,thick,fill=blue!3,rounded corners=1pt,text width=3.25cm,minimum height=1.15cm,align=left,font=\scriptsize},'
    printf '%s\n' '  association/.style={draw=reportgray,thick},'
    printf '%s\n' '  dependency/.style={draw=reportgray,thick,dashed,-{Latex[length=2mm]}}'
    printf '%s\n' '}'
    printf '%s\n' '\pagestyle{empty}'
    printf '%s\n' '\begin{document}'
    printf '%s\n' '\begin{preview}'
    printf '%s\n' '\noindent\resizebox{0.98\textwidth}{!}{%'
    printf '%s\n' '\input{diagram-body.tex}'
    printf '%s\n' '}'
    printf '%s\n' '\end{preview}'
    printf '%s\n' '\end{document}'
  } > "${TEMP_DIR}/diagram.tex"

  if ! (
    cd "${TEMP_DIR}"
    xelatex \
      -interaction=nonstopmode \
      -halt-on-error \
      -file-line-error \
      diagram.tex > xelatex-output.log
  ); then
    sed -n '1,240p' "${TEMP_DIR}/xelatex-output.log" >&2
    return 1
  fi

  pdftocairo -png -singlefile -r 220 \
    "${TEMP_DIR}/diagram.pdf" "${TEMP_DIR}/diagram" >/dev/null
  mv "${TEMP_DIR}/diagram.png" "${OUTPUT_DIR}/${output_name}.png"
}

render_diagram "02-系统建模报告" 1 "02-01-use-case"
render_diagram "02-系统建模报告" 2 "02-02-domain-model"
render_diagram "02-系统建模报告" 3 "02-03-publish-sequence"
render_diagram "02-系统建模报告" 4 "02-04-claim-state"
render_diagram "03-架构设计文档" 1 "03-01-system-context"
render_diagram "03-架构设计文档" 2 "03-02-layered-jobs"
render_diagram "03-架构设计文档" 3 "03-03-publish-job-flow"
render_diagram "04-软件工程化说明文档" 1 "04-01-ci-pipeline"
render_diagram "05-软件测试与质量保证报告" 1 "05-01-test-levels"
render_diagram "05-软件测试与质量保证报告" 2 "05-02-defect-loop"
render_diagram "06-软件配置与运维文档" 1 "06-01-deployment-topology"
render_diagram "07-团队报告" 1 "07-01-team-collaboration"

echo "[diagram] exported 12 previews to ${OUTPUT_DIR}"
