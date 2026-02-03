class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        self._celsius = value

    @property
    def fahrenheit(self):
        return (self._celsius * 9/5) + 32

    @fahrenheit.setter
    def fahrenheit(self, value):
        self._celsius = (value - 32) * 5/9


temp = Temperature(25)
print(f"Температура у °C: {temp.celsius}")
print(f"Температура у °F: {temp.fahrenheit}")


temp.fahrenheit = 212
print("\nПісля зміни:")
print(f"Температура у °C: {temp.celsius:.2f}")
print(f"Температура у °F: {temp.fahrenheit:.2f}")
