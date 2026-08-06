from ai_workflow_lab.models import FixedResponseModel


def test_fixed_response_model_never_depends_on_input() -> None:
    model = FixedResponseModel("fixed", stream_chunks=("fi", "xed"))

    assert model.invoke([{"role": "user", "content": "ignored"}]) == "fixed"
    assert list(model.stream([])) == ["fi", "xed"]

