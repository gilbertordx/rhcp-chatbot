FROM node:18

WORKDIR /logbook
COPY ../package.json /logbook
RUN npm install
COPY . /logbook
CMD npm start

