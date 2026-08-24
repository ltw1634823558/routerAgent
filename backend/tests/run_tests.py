"""
测试运行脚本
PowerShell 激活环境: .\\.venv\\Scripts\\Activate.ps1
运行所有测试: pytest tests/ -v
运行特定类型测试: pytest tests/ -v -m unit
运行并生成覆盖率报告: pytest tests/ -v --cov=app --cov-report=html
"""
import subprocess
import sys


def run_tests(test_type: str = "all", verbose: bool = True, coverage: bool = False):
    """
    运行测试

    Args:
        test_type: 测试类型 (all, unit, integration, api, websocket, agent)
        verbose: 是否显示详细输出
        coverage: 是否生成覆盖率报告
    """
    cmd = ["python", "-m", "pytest", "tests/"]

    if verbose:
        cmd.append("-v")

    if test_type != "all":
        cmd.extend(["-m", test_type])

    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="运行 RouterAgent 测试")
    parser.add_argument(
        "--type",
        "-t",
        choices=["all", "unit", "integration", "api", "websocket", "agent"],
        default="all",
        help="测试类型",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--coverage", "-c", action="store_true", help="生成覆盖率报告")

    args = parser.parse_args()

    exit_code = run_tests(
        test_type=args.type, verbose=args.verbose, coverage=args.coverage
    )
    sys.exit(exit_code)
