FROM maven:3.9-eclipse-temurin-17 AS build
ENV MAVEN_OPTS="-Xmx512m"
WORKDIR /build
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src/ src/
RUN mvn package -DskipTests -B

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /build/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["sh", "-c", "java ${JAVA_OPTS:--Xms128m -Xmx256m} -jar app.jar"]
