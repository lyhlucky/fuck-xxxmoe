const JavaScriptObfuscator = require('javascript-obfuscator');
const fs = require('fs');
const path = require('path');
const glob = require('glob');
const archiver = require('archiver');
const minimist = require('minimist');

const inputDir = './src';
const outputDir = './dist/obfuscated';

const args = minimist(process.argv.slice(2));
const version = args.v || 'unknown';
const zipFilePath = `./dist/dl_${version}_scripts.zip`;
async function obfuscateFiles() {
    // 从 config.json 文件中读取混淆设置
    const config = JSON.parse(fs.readFileSync('./obfuscator.config.json', 'utf8'));

    // 使用 glob 同步获取当前目录下的所有 .js 文件
    const files = glob.sync(`${inputDir}/*.js`);

    // 确保输出目录存在
    fs.mkdirSync(outputDir, { recursive: true });

    // 遍历所有 .js 文件
    for (const file of files) {
        try {
            // 读取文件内容
            const fileContent = await fs.promises.readFile(file, 'utf8');

            // 使用配置文件中的设置混淆文件内容
            const obfuscationResult = JavaScriptObfuscator.obfuscate(fileContent, config);

            // 获取混淆后的代码
            const obfuscatedCode = obfuscationResult.getObfuscatedCode();

            // 获取输出文件的路径
            const outputFilePath = path.join(outputDir, path.basename(file));

            // 将混淆后的代码写入输出文件
            await fs.promises.writeFile(outputFilePath, obfuscatedCode);
        } catch (err) {
            console.error(`Error while processing file ${file}:`, err);
        }
    }

    // 创建 ZIP 存档
    const archive = archiver('zip', {
        zlib: { level: 9 }, // 设置压缩级别
    });

    // 创建一个可以写入 ZIP 文件的文件流
    const output = fs.createWriteStream(zipFilePath);

    // 管道存档数据到文件
    archive.pipe(output);

    // 将混淆后的文件添加到 ZIP 存档
    archive.directory(outputDir, false);

    // 监听存档完成事件
    output.on('close', () => {
        console.log('ZIP file created:', zipFilePath);
    });

    // 完成存档
    await archive.finalize();
}

obfuscateFiles().catch(err => console.error('Error:', err));