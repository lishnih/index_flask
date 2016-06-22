#!/usr/bin/env python
# coding=utf-8
# Stan 2016-06-19

from __future__ import ( division, absolute_import,
                         print_function, unicode_literals )

import os, logging

from wtforms import Form, BooleanField, StringField, PasswordField, validators

from .models import User


class RegistrationForm(Form):
    email = StringField('Email Address *', [
        validators.Length(min=6, max=40)
    ])
    username = StringField('Username *', [
        validators.Length(min=6, max=40)
    ])
    name = StringField('Name *', [
        validators.Length(min=3)
    ])
    company = StringField('Company')
    password = PasswordField('New Password *', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password *')
    accept_tos = BooleanField('I accept the TOS', [
        validators.DataRequired()
    ])

    def validate(self):
        validated = True

        rv = Form.validate(self)
        if not rv:
            validated = False

        user = User.query.filter_by(email=self.email.data).first()
        if user:
            self.email.errors.append('Email already registered')
            validated = False

        user = User.query.filter_by(username=self.username.data).first()
        if user:
            self.username.errors.append('Username already registered')
            validated = False

        return validated


class LoginForm(Form):
    email = StringField('Email', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])
    remember = BooleanField('Remember me')

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        user = User.query.filter_by(email=self.email.data).first()
        if user is None:
            self.email.errors.append('Invalid email or password')
            self.password.errors.append('Invalid email or password')
            return False

        password = user.get_password(self.password.data)
        if password != user.password:
            self.email.errors.append('Invalid email or password')
            self.password.errors.append('Invalid email or password')
            return False

        self.user = user
        return True
