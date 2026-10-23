# Maintainer: Gabriel VM <gabriel.vargas@bold.co>
pkgname=azure-cli
pkgver=0.3.0
pkgrel=1
pkgdesc="A comprehensive CLI tool to interact with Azure DevOps (Work Items, PRs, and more)."
arch=('any')
url="https://github.com/vmgabriel/azure-cli"
license=('MIT')
depends=('python' 'python-typer' 'python-requests' 'python-pydantic' 'python-pydantic-settings' 'python-beautifulsoup4' 'python-rich')
makedepends=('python-build' 'python-installer' 'python-hatchling')
checkdepends=('python-pytest' 'python-pytest-cov')
source=("$pkgname-$pkgver.tar.gz::https://github.com/vmgabriel/azure-cli/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP') # ⚠️ Actualizar con el hash real en un release formal

build() {
  cd "$pkgname-$pkgver"
  # Forzamos el uso del python del sistema y creamos un entorno aislado limpio
  /usr/bin/python -m build --wheel
}

check() {
  cd "$pkgname-$pkgver"

  # 🔑 CLAVE: Añadimos el directorio 'src' al PYTHONPATH.
  # Esto permite que pytest resuelva las importaciones de 'azure_cli'
  # antes de que el paquete sea instalado formalmente en el paso package().
  export PYTHONPATH="$PWD/src:$PYTHONPATH"

  # Ejecutamos solo pruebas unitarias (las de integración requieren PAT y red)
  /usr/bin/python -m pytest tests/unit -v
}

package() {
  cd "$pkgname-$pkgver"
  # Instalamos el wheel generado en el directorio de empaquetado de Arch
  /usr/bin/python -m installer --destdir="$pkgdir" dist/*.whl

  # Instalamos el archivo de licencia (Requisito estricto de Arch Linux)
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
