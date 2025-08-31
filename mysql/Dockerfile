FROM mysql:8.4.6

# Install tzdata on Oracle Linux base (no apt-get here)
RUN microdnf update -y \
 && microdnf install -y tzdata \
 && microdnf clean all

# Copy config and fix permissions
COPY ./my.cnf /etc/mysql/conf.d/my.cnf
RUN chmod 644 /etc/mysql/conf.d/my.cnf
