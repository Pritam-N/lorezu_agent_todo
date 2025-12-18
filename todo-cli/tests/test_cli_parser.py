def test_parser_accepts_stats_json():
    from todo_cli.cli import build_parser

    p = build_parser()
    args = p.parse_args(["stats", "--json"])
    assert args.cmd == "stats"
    assert args.json is True


def test_parser_accepts_done_without_id():
    from todo_cli.cli import build_parser

    p = build_parser()
    args = p.parse_args(["done"])
    assert args.cmd == "done"
    assert args.id is None
