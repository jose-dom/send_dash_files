import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output
import plotly.io as pio
from IPython.display import HTML, Image
from email.message import EmailMessage
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
import base64
import pandas as pd
import pathlib
import boto3
import requests   

# s3 resource
s3 = boto3.resource(
    service_name='s3',
    region_name=os.environ.get("AWS_DEFAULT_REGION"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)
bucket = s3.Bucket(os.environ.get("AWS_BUCKET_NAME")) 
df = pd.read_csv('solar.csv')

if not os.path.exists("files"):
    os.mkdir("files")


PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("files").resolve()

fig = go.Figure(
    data=[go.Bar(y=[2, 1, 3])],
    layout_title_text="Native Plotly rendering in Dash"
)

app = dash.Dash( __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}])

server = app.server

app.layout = html.Div(
    children = [
    dcc.Graph(id="graph", figure=fig),
    dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
    ),
    html.Div(dcc.Input(id='email-to-send', type='text')),
    html.Button('Submit', id='submit-val', n_clicks=0),
    html.Div(id='container-button-basic', children=[])
    ],
    id="main",
)

@app.callback(
    Output(component_id="container-button-basic",component_property="children"),
    Input(component_id="main",component_property="children"),
    Input(component_id="submit-val",component_property="n_clicks"),
    Input(component_id="email-to-send",component_property="value"),
)
def email_plot(children, n_clicks, email):
    # waiting for click
    if n_clicks != 0 or None:
        # creating list of charts
        charts=[]

        # grabbing all figures and tables and converting to files and adding paths to list
        for i in range(len(children)):
            obj = list(children[i]["props"].keys())
            if ("figure" in obj):
                fig_dict = children[i]["props"]["figure"]
                path = f"{DATA_PATH}/fig{i}.png"
                fig = go.Figure(fig_dict).write_image(path)
                charts.append(path)
                bucket.upload_file(Filename=path, Key=os.path.basename(path))
            elif ("columns" in obj):
                tbl_data = children[i]["props"]["data"]
                path = f"{DATA_PATH}/table{i}.csv"
                print(path)
                tbl = pd.DataFrame.from_dict(tbl_data).to_csv(path, index=False)
                charts.append(path)
                bucket.upload_file(Filename=path, Key=os.path.basename(path))

        # generating email info
        me  = os.environ.get("EMAIL_USER")
        recipient = email
        subject = 'Graph Report'

        # server info
        email_server_host = 'smtp.office365.com'
        port = 587
        email_username = me
        email_password = os.environ.get("EMAIL_PASS")

        # email message info
        msg = MIMEMultipart()
        msg['From'] = me
        msg['To'] = recipient
        msg['Subject'] = subject

        # attach text to message
        text = MIMEText("Test Email")
        msg.attach(text)

        # for each file attach to the message with a name
        for i in charts:
            # removing "files/" path from name
            file_name = os.path.basename(i)
            get_file = bucket.Object(file_name).get()["Body"]
            msg.attach(MIMEApplication(get_file.read(), Name=file_name))
        
        # send email
        server = smtplib.SMTP(email_server_host, port)
        server.ehlo()
        server.starttls()
        server.login(email_username, email_password)
        server.sendmail(me, recipient, msg.as_string())
        server.close()

        # success message to user
        success_msg = "Email of figure sent to " + str(email)
        return html.P(success_msg)

if __name__ == "__main__":
    app.run_server(debug=True, host='localhost', port=8000)