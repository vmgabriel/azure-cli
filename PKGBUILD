# Maintainer: Gabriel VM <gabriel.vargas@bold.co>
pkgname=azure-cli
pkgver=0.1.0
pkgrel=1
pkgdesc="A comprehensive CLI tool to interact with Azure DevOps (Work Items, PRs, and more)."
arch=('any')
url="https://github.com/vmgabriel/azure-cli"
license=('MIT')
depends=('python' 'python-typer' 'python-requests' 'python-pydantic' 'python-pydantic-settings' 'python-beautifulsoup4' 'python-rich')
makedepends=('python-build' 'python-installer' 'python-hatchling')
checkdepends=('python-pytest' 'python-pytest-cov')
source=("$pkgname-$pkgver.tar.gz::https://github.com/vmgabriel/azure-cli/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP') # ⚠️ Actualizar con el hash real al crear el tag git

build() {
  cd "$pkgname-$pkgver"
  # Construye el wheel usando el backend declarado en pyproject.toml
  python -m build --wheel --no-isolation
}

check() {
  cd "$pkgname-$pkgver"
  # Ejecuta solo pruebas unitarias en el chroot limpio (las de integración requieren PAT)
  python -m pytest tests/unit
}

package() {
  cd "$pkgname-$pkgver"
  # Instala el wheel de forma limpia en el directorio de empaquetado
  python -m installer --destdir="$pkgdir" dist/*.whl

  # Instala la licencia (requiere que el archivo LICENSE exista en la raíz)
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
