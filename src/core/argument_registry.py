from src.schemas.arguments import (
    Argument,
    ArgumentRecord,
    ArgumentStatus,
    FactCheck,
    FactCheckVerdict,
    Rebuttal,
)


class ArgumentRegistry:
    def __init__(self, data: dict[str, ArgumentRecord] | None = None):
        self._arguments: dict[str, ArgumentRecord] = dict(data) if data else {}

    def register(self, arg: Argument, round_num: int, agent: str) -> None:
        """注册新论点"""
        self._arguments[arg.id] = ArgumentRecord(
            argument=arg,
            raised_in_round=round_num,
            raised_by=agent,
        )

    def update_status(self, arg_id: str, new_status: ArgumentStatus, reason: str = "") -> None:
        """更新论点状态"""
        if arg_id in self._arguments:
            record = self._arguments[arg_id]
            record.argument.status = new_status
            if reason:
                record.modification_history.append(reason)

    def add_rebuttal(self, arg_id: str, rebuttal: Rebuttal) -> None:
        """给论点添加反驳记录"""
        if arg_id in self._arguments:
            self._arguments[arg_id].rebuttals.append(rebuttal)

    def add_fact_check(self, arg_id: str, check: FactCheck) -> None:
        """给论点添加校验记录"""
        if arg_id in self._arguments:
            self._arguments[arg_id].fact_checks.append(check)
            if check.verdict == FactCheckVerdict.FLAWED:
                self.update_status(
                    arg_id,
                    ArgumentStatus.REBUTTED,
                    f"Fact-check: {check.explanation}",
                )

    def get_active_arguments(self, side: str | None = None) -> list[ArgumentRecord]:
        """获取所有存活论点，可按阵营过滤"""
        results = [
            r for r in self._arguments.values()
            if r.argument.status in (ArgumentStatus.ACTIVE, ArgumentStatus.MODIFIED)
        ]
        if side:
            results = [r for r in results if r.raised_by == side]
        return results

    def get_survivor_stats(self) -> dict:
        """生成论点存活统计"""
        total = len(self._arguments)
        active = len([
            r for r in self._arguments.values()
            if r.argument.status in (ArgumentStatus.ACTIVE, ArgumentStatus.MODIFIED)
        ])
        return {
            "total_raised": total,
            "survived": active,
            "rebutted": len([
                r for r in self._arguments.values()
                if r.argument.status == ArgumentStatus.REBUTTED
            ]),
            "conceded": len([
                r for r in self._arguments.values()
                if r.argument.status == ArgumentStatus.CONCEDED
            ]),
        }

    def to_dict(self) -> dict[str, ArgumentRecord]:
        return dict(self._arguments)
