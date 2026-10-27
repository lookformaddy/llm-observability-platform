.PHONY: test demo run

test:
	python -m pytest -q

demo:
	python -m llm_observability

run:
	uvicorn llm_observability.service:app --port 8000
