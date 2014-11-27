app = angular.module "toddlerWebApp", [
  'ngCookies',
  'ngRoute',
  'ngLocalize',
  'ui.bootstrap',
  'dialogs.main'
]

app.value 'localeSupported', [
  "en-GB"
]

app.value 'localeFallbacks',
  'en': 'en-GB'

app.value 'localeConf',
  basePath: 'static/languages',
  defaultLocale: 'en-GB',
  sharedDictionary: 'common',
  fileExtension: '.lang.json',
  persistSelection: true,
  cookieName: 'COOKIE_LOCALE_LANG',
  observableAttrs: new RegExp('^data-(?!ng-|i18n)'),
  delimiter: '::'

app.run ($http, $cookies, $interval, $location, $rootScope) ->

  $rootScope.logged_in = false
  $http.defaults.headers.post['X-CSRF-TOKEN'] = $cookies['csrf_token']
  $http.defaults.headers.common['X-CSRF-TOKEN'] = $cookies['csrf_token']

  $rootScope.$on "$routeChangeStart", (event, next, current) ->
    if not $rootScope.logged_in and next.templateUrl isnt "/partials/login.html"
      $location.path("/login")


  checkAuth = () ->
    if $location.path() isnt "/login"
      $http.get("/api/v1/is-logged-in")
      .then (response) ->
        $rootScope.logged_in = true

  $interval(checkAuth, 3600000)
  checkAuth()

app.factory "authHttpInterceptor", ($q, $location, $rootScope) ->
  responseError: (response) ->
    if $location.path() isnt "/login"
      if response.status is 401
        $rootScope._redirectAfterlogin = $location.path()
        $rootScope.logged_in = false
        $location.path("/login")
    $q.reject(response)

app.config ($routeProvider, $locationProvider, $provide, $httpProvider) ->

  $httpProvider.interceptors.push("authHttpInterceptor")

  $routeProvider
  .when "/",
    controller: "UrlsController",
    templateUrl: "partials/report-urls.html"
  .when "/login",
    controller: "LoginController",
    templateUrl: "partials/login.html"

  $locationProvider.html5Mode true