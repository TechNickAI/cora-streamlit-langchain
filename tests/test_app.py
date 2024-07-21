from streamlit.testing.v1 import AppTest


def test_app_load():
    # Initialize the AppTest with the Streamlit app file
    at = AppTest.from_file("streamlit_app.py")
    at.run()
