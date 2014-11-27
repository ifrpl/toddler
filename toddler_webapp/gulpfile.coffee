gulp = require "gulp"
jade = require "gulp-jade"
coffee = require "gulp-coffee"
streamqueue = require "streamqueue"
uglify = require "gulp-uglify"
order = require "gulp-order"
del = require "del"
glob = require "glob"
minifyCss = require "gulp-minify-css"
_ = require "lodash"
fs = require "fs"
ngHtml2Js = require "gulp-ng-html2js"
concat = require "gulp-concat"
concatCss = require "gulp-concat-css"
htmlPrettify = require "gulp-html-prettify"
rename = require "gulp-rename"

# directory config
SRC_DIR = "./web-src/"
DEST_DIR = "./static/"


# bower requirements
BOWER_COMPONENTS_JS = [
  "angular/angular.js",
  "angular-bootstrap/ui-bootstrap-tpls.js",
  "angular-cookies/angular-cookies.js",
  "angular-localization/angular-localization.js",
  "angular-sanitize/angular-sanitize.js",
  "angular-route/angular-route.js",
  "angular-dialog-service/dist/dialogs.min.js",
  "lodash/dist/lodash.js"
]

BOWER_COMPONENTS_CSS = [
  "angular-dialog-service/dist/dialogs.min.css"
  "font-awesome/css/font-awesome.css"
]


gulp.task "clean-js", (cb) ->
  del glob.sync(DEST_DIR+"/**/*.js"), cb

gulp.task "js-dev", ['clean-js'], ->

  streamqueue objectMode: true,
    gulp.src SRC_DIR+"/**/*.coffee"
    .pipe coffee()
    gulp.src SRC_DIR+"/**/*.js"
  .pipe(gulp.dest DEST_DIR+"/")

gulp.task "clean-css", (cb) ->
  del glob.sync(DEST_DIR+"/**/*.css"), cb

gulp.task "css", ['clean-css'], ->
#  add less leater if needed
  gulp.src SRC_DIR+"/**/*.css"
  .pipe gulp.dest(DEST_DIR+"/css/")


# angular localisation languages
gulp.task "languages", ->
  gulp.src [SRC_DIR + "/**/*.lang.json"]
  .pipe gulp.dest(DEST_DIR+"/")

gulp.task "fonts", ->
  gulp.src "bower_components/**/*.{eot,otf,svg,ttf,woff}"
  .pipe rename({'dirname':''})
  .pipe gulp.dest(DEST_DIR+"/css/fonts/")

# compiling partials to one js file
gulp.task "partials", ->

  gulp.src SRC_DIR+"/partials/**/*.jade"
  .pipe jade()
  .pipe ngHtml2Js
    moduleName: "toddlerWebApp",
    prefix: "partials/"
  .pipe concat("partials.min.js")
  .pipe gulp.dest(DEST_DIR + "/js/partials/")

# main jade file compiling
gulp.task "jade", ->
  jsFiles = _(glob.sync(DEST_DIR+"/**/*.js"))
  .map((file) ->
    file.replace(DEST_DIR, "/static/")
  )
  .sortBy((file) ->
    (file.match(/\//g) or []).length
  )
  .value()

  cssFiles = _(glob.sync(DEST_DIR+"/**/*.css"))
  .map((file) ->
    file.replace(DEST_DIR, "/static/")
  ).value()

  bower_components_css = _(BOWER_COMPONENTS_CSS)
  .map((file) ->
    "/static/b/"+file
  ).value()

  bower_components_js = _(BOWER_COMPONENTS_JS)
  .map((file) ->
    "/static/b/"+file
  ).value()

  js_files = _.union(bower_components_js, jsFiles)
  css_files = _.union(bower_components_css, cssFiles)

  bowerConfig = JSON.parse(fs.readFileSync('bower.json', 'utf8'))

  gulp.src SRC_DIR+"/index.jade"
  .pipe jade
    locals:
      cssFiles: css_files
      jsFiles: js_files
      version: bowerConfig.version
  .pipe htmlPrettify({indent_char: ' ', indent_size: 2})
  .pipe gulp.dest(DEST_DIR+"/")

gulp.task "dev", ['js-dev', 'css', 'partials', 'languages', 'jade', 'fonts']

gulp.task "watch", ['dev'], ->
  gulp.watch SRC_DIR+"/index.jade", ['jade']
  gulp.watch SRC_DIR+"/partials/**/*.jade", ['partials']
  gulp.watch SRC_DIR+"/**/*.{js,coffee}", ['js-dev', 'partials']
  gulp.watch SRC_DIR+"/**/**.lang.json", ['languages']
  gulp.watch SRC_DIR+"/**/**.{less,css}", ['css']
