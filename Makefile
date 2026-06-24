update:
	conda run -n fgi python3 src/vkospi_update.py

run:
	source venv/bin/activate && streamlit run src/fear_greed_index.py

clean:
	rm -f data/*.csv

install:
	pip install -r requirements.txt

install-fgi:
	conda run -n fgi pip install -r requirements_fgi.txt
