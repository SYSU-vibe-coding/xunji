#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

build_report() {
  local directory="$1"
  local job_name="$2"

  echo "[report] building ${directory}/${job_name}.pdf"
  cd "${ROOT_DIR}/${directory}"
  xelatex -interaction=nonstopmode -halt-on-error -file-line-error -jobname="${job_name}" main.tex
  xelatex -interaction=nonstopmode -halt-on-error -file-line-error -jobname="${job_name}" main.tex
  xelatex -interaction=nonstopmode -halt-on-error -file-line-error -jobname="${job_name}" main.tex
}

build_report "01-需求分析报告" "24325356朱梓涵需求分析报告"
build_report "02-系统建模报告" "24325356朱梓涵系统建模报告"
build_report "03-架构设计文档" "24325356朱梓涵架构设计文档"
build_report "04-软件工程化说明文档" "24325356朱梓涵软件工程化说明文档"
build_report "05-软件测试与质量保证报告" "24325356朱梓涵软件测试与质量保证报告"
build_report "06-软件配置与运维文档" "24325356朱梓涵软件配置与运维文档"
build_report "07-团队报告" "24325356朱梓涵团队报告"

source "${ROOT_DIR}/export-diagrams.sh"

echo "[report] all reports built"
