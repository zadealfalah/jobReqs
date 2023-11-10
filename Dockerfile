FROM python:3.9

WORKDIR /srv

# Add only necessary files
ADD requirements.txt /srv
ADD lambda_function.py /srv
ADD Dockerfile /srv
ADD .dockerignore /srv

RUN apt-get -y update \
    && apt-get install -y zip unzip \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install --pre selenium 
    
# Install latest Chrome
RUN CHROME_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chrome[] | select(.platform == "linux64") | .url') \
    && curl -sSLf --retry 3 --output /tmp/chrome-linux64.zip "$CHROME_URL" \
    && unzip /tmp/chrome-linux64.zip -d /opt \
    && ln -s /opt/chrome-linux64/chrome /usr/local/bin/chrome \
    && rm /tmp/chrome-linux64.zip

# Install latest chromedriver
RUN CHROMEDRIVER_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform == "linux64") | .url') \
    && curl -sSLf --retry 3 --output /tmp/chromedriver-linux64.zip "$CHROMEDRIVER_URL" \
    && unzip -o /tmp/chromedriver-linux64.zip -d /tmp \
    && rm -rf /tmp/chromedriver-linux64.zip \
    && mv -f /tmp/chromedriver-linux64/chromedriver "/usr/local/bin/chromedriver" \
    && chmod +x "/usr/local/bin/chromedriver"

# # Install chromedriver
# RUN wget -N https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/119.0.6045.105/linux64/chromedriver-linux64.zip -P ~/
# RUN unzip ~/chromedriver-linux64.zip -d ~/
# RUN rm ~/chromedriver-linux64.zip
# RUN mv -f ~/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
# RUN chown root:root /usr/local/bin/chromedriver
# RUN chmod 0755 /usr/local/bin/chromedriver

# # # Install chrome browser
# RUN wget -N https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/119.0.6045.105/linux64/chrome-linux64.zip -P ~/
# RUN unzip ~/chrome-linux64.zip -d /opt/
# RUN rm ~/chrome-linux64.zip
# RUN ln -s /opt/chrome-linux64/chrome /usr/local/bin/chrome
# # # Add the Google Chrome repository key
# # RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
# # RUN echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
# # RUN apt-get -y update \
# #     && apt-get -y install google-chrome-stable

CMD ["python", "lambda_function.py"]

