cat > startup.sh << 'EOF'
#!/bin/bash
export DJANGO_SETTINGS_MODULE=my_django_project.settings
gunicorn my_django_project.wsgi --bind 0.0.0.0:\$PORT
EOF

chmod +x startup.sh
