# video-download-scripts


### Setup

Make sure to install the dependencies:

```bash
# npm
npm install

# yarn
yarn install
```
### Obfuscate & Compress

Obfuscated files in the `./dist/obfuscated` directory, compressed file is `./dist/dl_[<version>|unknown]_scripts.zip'`.

```bash
# npm
npm run build [-- --v=<version>] # eg: npm run build -- --v=3.0.0

# yarn
yarn build [-- --v=<version>] # eg: yarn build -- --v=3.0.0
```
