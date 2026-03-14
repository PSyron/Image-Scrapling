from svg_scrapling.__main__ import build_parser


def test_build_parser_has_program_name() -> None:
    parser = build_parser()

    assert parser.prog == "assets"
